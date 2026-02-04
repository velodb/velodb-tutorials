#!/usr/bin/env python3
"""
VeloDB User Analytics - Real-time Data Generator

Generates continuous event and conversion data into PostgreSQL.
All 5 tables are synced to VeloDB via Flink CDC:
- Dimension tables: dim_users, dim_features, dim_campaigns
- Fact tables: fact_events, fact_conversions

Optional: Also streams to Kafka for demonstrating dual-path ingestion.
"""

import os
import json
import time
import random
import signal
import sys
import threading
from datetime import datetime
from typing import Optional

import psycopg2
from psycopg2 import Error

# Optional Kafka support
try:
    from kafka import KafkaProducer
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    print("[INFO] kafka-python not installed, Kafka streaming disabled")

# Configuration from environment
POSTGRES_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': int(os.getenv('POSTGRES_PORT', 5432)),
    'user': os.getenv('POSTGRES_USER', 'labuser'),
    'password': os.getenv('POSTGRES_PASSWORD', 'labpass'),
    'database': os.getenv('POSTGRES_DB', 'user_analytics'),
}

KAFKA_CONFIG = {
    'bootstrap_servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
    'enabled': os.getenv('KAFKA_ENABLED', 'false').lower() == 'true',
}

# Data generation rates
EVENTS_PER_SECOND = float(os.getenv('EVENTS_PER_SECOND', 5))
CONVERSION_INTERVAL = float(os.getenv('CONVERSION_INTERVAL', 5))  # seconds between conversions
NEW_USER_INTERVAL = float(os.getenv('NEW_USER_INTERVAL', 30))  # seconds between new users

# Event types and pages
EVENT_TYPES = ['page_view', 'feature_use', 'search', 'click', 'scroll', 'form_start', 'form_submit', 'error']
PAGES = ['/app/dashboard', '/app/analytics', '/app/settings', '/app/reports', '/app/integrations']
SEARCH_QUERIES = [
    'how to dashboard', 'create report', 'export data', 'analyze users',
    'integrate api', 'build chart', 'filter results', 'share dashboard'
]
CONVERSION_TYPES = ['signup', 'upgrade', 'purchase', 'churn']
PLANS = ['Free', 'Pro', 'Enterprise']
COUNTRIES = ['USA', 'UK', 'Germany', 'Japan', 'Brazil', 'India', 'Canada', 'Australia']
INDUSTRIES = ['Technology', 'Finance', 'Healthcare', 'Retail', 'Education', 'Manufacturing']
FIRST_NAMES = ['Alex', 'Sam', 'Jordan', 'Taylor', 'Morgan', 'Casey', 'Riley', 'Quinn', 'Avery', 'Blake']
LAST_NAMES = ['Chen', 'Smith', 'Garcia', 'Kim', 'Patel', 'Mueller', 'Santos', 'Nguyen', 'Johnson', 'Lee']
EMAIL_DOMAINS = ['gmail.com', 'company.com', 'outlook.com', 'startup.io', 'tech.co']


class DataGenerator:
    """Generates continuous data for PostgreSQL (and optionally Kafka)."""

    def __init__(self):
        self.conn: Optional[psycopg2.extensions.connection] = None
        self.kafka_producer = None
        self.running = True

        # Track IDs
        self.max_user_id = 0
        self.max_feature_id = 0
        self.max_campaign_id = 0
        self.max_event_id = 0
        self.max_conversion_id = 0

        # Stats
        self.events_generated = 0
        self.conversions_generated = 0

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        print("\n[INFO] Shutting down gracefully...")
        self.running = False

    def connect_postgres(self) -> bool:
        """Establish PostgreSQL connection."""
        max_retries = 30
        for i in range(max_retries):
            try:
                self.conn = psycopg2.connect(**POSTGRES_CONFIG)
                self.conn.autocommit = True
                print(f"[PostgreSQL] Connected to {POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG['port']}/{POSTGRES_CONFIG['database']}")
                return True
            except Error as e:
                print(f"[PostgreSQL] Connection attempt {i+1}/{max_retries} failed: {e}")
                time.sleep(2)
        return False

    def connect_kafka(self) -> bool:
        """Establish Kafka connection (optional)."""
        if not KAFKA_AVAILABLE or not KAFKA_CONFIG['enabled']:
            return False

        try:
            self.kafka_producer = KafkaProducer(
                bootstrap_servers=KAFKA_CONFIG['bootstrap_servers'],
                value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
            )
            print(f"[Kafka] Connected to {KAFKA_CONFIG['bootstrap_servers']}")
            return True
        except Exception as e:
            print(f"[Kafka] Connection failed: {e}")
            return False

    def get_max_ids(self) -> bool:
        """Load current max IDs from database."""
        try:
            cursor = self.conn.cursor()

            cursor.execute("SELECT COALESCE(MAX(user_id), 0) FROM dim_users")
            self.max_user_id = cursor.fetchone()[0]

            cursor.execute("SELECT COALESCE(MAX(feature_id), 0) FROM dim_features")
            self.max_feature_id = cursor.fetchone()[0]

            cursor.execute("SELECT COALESCE(MAX(campaign_id), 0) FROM dim_campaigns")
            self.max_campaign_id = cursor.fetchone()[0]

            cursor.execute("SELECT COALESCE(MAX(event_id), 0) FROM fact_events")
            self.max_event_id = cursor.fetchone()[0]

            cursor.execute("SELECT COALESCE(MAX(conversion_id), 0) FROM fact_conversions")
            self.max_conversion_id = cursor.fetchone()[0]

            cursor.close()

            print(f"[INFO] Current max IDs - users:{self.max_user_id}, features:{self.max_feature_id}, "
                  f"campaigns:{self.max_campaign_id}, events:{self.max_event_id}, conversions:{self.max_conversion_id}")

            if self.max_user_id == 0 or self.max_feature_id == 0 or self.max_campaign_id == 0:
                print("[ERROR] Dimension tables are empty. Seed data should be loaded via init_postgres.sql")
                return False
            return True
        except Error as e:
            print(f"[ERROR] Failed to get max IDs: {e}")
            return False

    def add_new_user(self):
        """Add a new user to simulate organic growth."""
        self.max_user_id += 1
        i = self.max_user_id

        name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        email = f"user{i}@{random.choice(EMAIL_DOMAINS)}"
        signup_date = datetime.now().strftime('%Y-%m-%d')
        plan = random.choice(PLANS)
        country = random.choice(COUNTRIES)
        industry = random.choice(INDUSTRIES)

        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """INSERT INTO dim_users (user_id, email, name, signup_date, plan, country, industry)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (i, email, name, signup_date, plan, country, industry)
            )
            cursor.close()
            print(f"[NEW USER] {name} ({email}) joined with {plan} plan")
        except Error as e:
            print(f"[ERROR] Failed to add user: {e}")
            self.max_user_id -= 1

    def generate_event(self):
        """Generate and insert a single event."""
        self.max_event_id += 1
        event_type = random.choice(EVENT_TYPES)

        event = {
            'event_id': self.max_event_id,
            'user_id': random.randint(1, self.max_user_id),
            'feature_id': random.randint(1, self.max_feature_id),
            'campaign_id': random.randint(1, self.max_campaign_id),
            'session_id': f"sess_{random.randint(1, 100000)}",
            'event_type': event_type,
            'event_time': datetime.now(),
            'page_url': random.choice(PAGES),
            'search_query': random.choice(SEARCH_QUERIES) if event_type == 'search' else None,
            'properties': json.dumps({'duration': random.randint(1, 300), 'scroll_depth': random.randint(0, 100)})
        }

        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """INSERT INTO fact_events
                   (event_id, user_id, feature_id, campaign_id, session_id, event_type, event_time, page_url, search_query, properties)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (event['event_id'], event['user_id'], event['feature_id'], event['campaign_id'],
                 event['session_id'], event['event_type'], event['event_time'], event['page_url'],
                 event['search_query'], event['properties'])
            )
            cursor.close()
            self.events_generated += 1

            # Also send to Kafka if enabled
            if self.kafka_producer:
                self.kafka_producer.send('fact_events', event)

        except Error as e:
            print(f"[ERROR] Failed to insert event: {e}")
            self.max_event_id -= 1

    def generate_conversion(self):
        """Generate and insert a single conversion."""
        self.max_conversion_id += 1
        conv_type = random.choice(CONVERSION_TYPES)

        # Determine plan transitions
        if conv_type == 'signup':
            plan_from = None
            plan_to = random.choice(['Free', 'Pro'])
        elif conv_type == 'upgrade':
            plan_from = random.choice(['Free', 'Pro'])
            plan_to = 'Enterprise' if plan_from == 'Pro' else 'Pro'
        elif conv_type == 'churn':
            plan_from = random.choice(PLANS)
            plan_to = None
        else:  # purchase
            plan_from = random.choice(PLANS)
            plan_to = plan_from

        # Revenue based on conversion type
        if conv_type == 'upgrade':
            revenue = round(random.uniform(99, 499), 2)
        elif conv_type == 'purchase':
            revenue = round(random.uniform(10, 200), 2)
        elif conv_type == 'signup' and plan_to != 'Free':
            revenue = round(random.uniform(29, 99), 2)
        else:
            revenue = 0.0

        conversion = {
            'conversion_id': self.max_conversion_id,
            'user_id': random.randint(1, self.max_user_id),
            'feature_id': random.randint(1, self.max_feature_id),
            'campaign_id': random.randint(1, self.max_campaign_id),
            'conversion_type': conv_type,
            'conversion_time': datetime.now(),
            'plan_from': plan_from,
            'plan_to': plan_to,
            'revenue': revenue,
            'properties': json.dumps({'source': 'app'})
        }

        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """INSERT INTO fact_conversions
                   (conversion_id, user_id, feature_id, campaign_id, conversion_type, conversion_time, plan_from, plan_to, revenue, properties)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (conversion['conversion_id'], conversion['user_id'], conversion['feature_id'], conversion['campaign_id'],
                 conversion['conversion_type'], conversion['conversion_time'], conversion['plan_from'], conversion['plan_to'],
                 conversion['revenue'], conversion['properties'])
            )
            cursor.close()
            self.conversions_generated += 1
            print(f"[CONVERSION] {conv_type} - ${revenue:.2f}")

            # Also send to Kafka if enabled
            if self.kafka_producer:
                self.kafka_producer.send('fact_conversions', conversion)

        except Error as e:
            print(f"[ERROR] Failed to insert conversion: {e}")
            self.max_conversion_id -= 1

    def run(self):
        """Run continuous data generation."""
        print(f"[INFO] Starting data generation - {EVENTS_PER_SECOND} events/sec, "
              f"conversion every {CONVERSION_INTERVAL}s, new user every {NEW_USER_INTERVAL}s")

        event_interval = 1.0 / EVENTS_PER_SECOND if EVENTS_PER_SECOND > 0 else 1
        last_conversion = time.time()
        last_new_user = time.time()

        while self.running:
            # Generate event
            self.generate_event()

            # Generate conversion periodically
            if time.time() - last_conversion >= CONVERSION_INTERVAL:
                self.generate_conversion()
                last_conversion = time.time()

            # Add new user periodically
            if time.time() - last_new_user >= NEW_USER_INTERVAL:
                self.add_new_user()
                last_new_user = time.time()

            # Status update every 100 events
            if self.events_generated % 100 == 0:
                print(f"[STATUS] Events: {self.events_generated}, Conversions: {self.conversions_generated}, Users: {self.max_user_id}")

            time.sleep(event_interval)

        print(f"[INFO] Final stats - Events: {self.events_generated}, Conversions: {self.conversions_generated}")

    def disconnect(self):
        """Close connections."""
        if self.conn:
            self.conn.close()
            print("[PostgreSQL] Disconnected")
        if self.kafka_producer:
            self.kafka_producer.close()
            print("[Kafka] Disconnected")


def main():
    print("=" * 60)
    print("VeloDB User Analytics - Data Generator")
    print("=" * 60)
    print(f"PostgreSQL: {POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG['port']}/{POSTGRES_CONFIG['database']}")
    print(f"Kafka: {KAFKA_CONFIG['bootstrap_servers']} (enabled: {KAFKA_CONFIG['enabled']})")
    print(f"Rates: {EVENTS_PER_SECOND} events/sec")
    print("=" * 60)

    gen = DataGenerator()

    if not gen.connect_postgres():
        print("[ERROR] Failed to connect to PostgreSQL")
        sys.exit(1)

    gen.connect_kafka()  # Optional

    try:
        if not gen.get_max_ids():
            sys.exit(1)
        gen.run()
    finally:
        gen.disconnect()


if __name__ == '__main__':
    main()
