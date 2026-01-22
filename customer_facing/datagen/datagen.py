#!/usr/bin/env python3
"""
VeloDB User Behavior Analytics - Real-time Data Generator

Generates continuous realistic user behavior events for the 5-table star schema.
Assumes tables already exist and contain initial seed data.

Tables:
- dim_users, dim_features, dim_campaigns (dimensions)
- fact_events, fact_conversions (facts)

Usage:
    python datagen.py --host HOST --port PORT --user USER --password PASS --database DB
"""

import argparse
import random
import time
import signal
import sys
from datetime import datetime
from typing import Optional
import mysql.connector
from mysql.connector import Error

# Configuration
FIRST_NAMES = ['Alex', 'Sam', 'Jordan', 'Taylor', 'Morgan', 'Casey', 'Riley', 'Quinn', 'Avery', 'Blake']
LAST_NAMES = ['Chen', 'Smith', 'Garcia', 'Kim', 'Patel', 'Mueller', 'Santos', 'Nguyen', 'Johnson', 'Lee']
EMAIL_DOMAINS = ['gmail.com', 'company.com', 'outlook.com', 'startup.io', 'tech.co']
PLANS = ['Free', 'Pro', 'Enterprise']
COUNTRIES = ['USA', 'UK', 'Germany', 'Japan', 'Brazil', 'India', 'Canada', 'Australia']
INDUSTRIES = ['Technology', 'Finance', 'Healthcare', 'Retail', 'Education', 'Manufacturing']
DEVICES = ['desktop', 'mobile', 'tablet']
BROWSERS = ['Chrome', 'Safari', 'Firefox', 'Edge']

EVENT_TYPES = ['page_view', 'feature_use', 'search', 'click', 'scroll', 'form_start', 'form_submit', 'error']
PAGES = ['/app/dashboard', '/app/analytics', '/app/settings', '/app/reports', '/app/integrations']
SEARCH_QUERIES = [
    'how to dashboard', 'create report', 'export data', 'analyze users',
    'integrate api', 'build chart', 'filter results', 'share dashboard',
    'schedule report', 'custom metrics', 'user segments', 'funnel analysis'
]

CONVERSION_TYPES = ['signup', 'upgrade', 'purchase', 'churn']


class DataGenerator:
    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.conn: Optional[mysql.connector.MySQLConnection] = None
        self.running = True

        # Track generated IDs
        self.max_user_id = 0
        self.max_feature_id = 0
        self.max_campaign_id = 0
        self.max_event_id = 0
        self.max_conversion_id = 0

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        print("\n[INFO] Shutting down gracefully...")
        self.running = False

    def connect(self) -> bool:
        """Establish database connection."""
        try:
            self.conn = mysql.connector.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                autocommit=True
            )
            print(f"[INFO] Connected to {self.host}:{self.port}/{self.database}")
            return True
        except Error as e:
            print(f"[ERROR] Failed to connect: {e}")
            return False

    def disconnect(self):
        """Close database connection."""
        if self.conn and self.conn.is_connected():
            self.conn.close()
            print("[INFO] Disconnected from database")

    def execute(self, sql: str, params: tuple = None) -> bool:
        """Execute SQL statement."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, params)
            cursor.close()
            return True
        except Error as e:
            print(f"[ERROR] SQL execution failed: {e}")
            return False

    def query_one(self, sql: str) -> Optional[tuple]:
        """Execute query and return one row."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql)
            result = cursor.fetchone()
            cursor.close()
            return result
        except Error as e:
            print(f"[ERROR] Query failed: {e}")
            return None

    def get_max_ids(self):
        """Get current max IDs from tables."""
        result = self.query_one("SELECT COALESCE(MAX(user_id), 0) FROM dim_users")
        self.max_user_id = result[0] if result else 0

        result = self.query_one("SELECT COALESCE(MAX(feature_id), 0) FROM dim_features")
        self.max_feature_id = result[0] if result else 0

        result = self.query_one("SELECT COALESCE(MAX(campaign_id), 0) FROM dim_campaigns")
        self.max_campaign_id = result[0] if result else 0

        result = self.query_one("SELECT COALESCE(MAX(event_id), 0) FROM fact_events")
        self.max_event_id = result[0] if result else 0

        result = self.query_one("SELECT COALESCE(MAX(conversion_id), 0) FROM fact_conversions")
        self.max_conversion_id = result[0] if result else 0

        print(f"[INFO] Current max IDs - users:{self.max_user_id}, features:{self.max_feature_id}, "
              f"campaigns:{self.max_campaign_id}, events:{self.max_event_id}, conversions:{self.max_conversion_id}")

        # Validate that tables have data
        if self.max_user_id == 0 or self.max_feature_id == 0 or self.max_campaign_id == 0:
            print("[ERROR] Tables appear to be empty. Please run the tutorial SQL to create schema and seed data first.")
            return False
        return True

    def generate_event(self) -> dict:
        """Generate a single event."""
        self.max_event_id += 1

        event = {
            'event_id': self.max_event_id,
            'user_id': random.randint(1, self.max_user_id),
            'feature_id': random.randint(1, self.max_feature_id),
            'campaign_id': random.randint(1, self.max_campaign_id),
            'session_id': f"sess_{random.randint(1, 100000)}",
            'event_type': random.choice(EVENT_TYPES),
            'event_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'page_url': random.choice(PAGES),
            'search_query': random.choice(SEARCH_QUERIES) if random.random() < 0.15 else None,
            'properties': f'{{"duration":{random.randint(1, 300)},"scroll_depth":{random.randint(0, 100)}}}'
        }
        return event

    def generate_conversion(self) -> dict:
        """Generate a single conversion."""
        self.max_conversion_id += 1

        conv_type = random.choice(CONVERSION_TYPES)
        plan_from = random.choice([None, 'Free', 'Pro']) if conv_type != 'signup' else None
        plan_to = random.choice(['Pro', 'Enterprise']) if conv_type in ['signup', 'upgrade'] else None
        revenue = round(random.uniform(10, 500) if random.random() < 0.7 else random.uniform(500, 2000), 2)

        conversion = {
            'conversion_id': self.max_conversion_id,
            'user_id': random.randint(1, self.max_user_id),
            'feature_id': random.randint(1, self.max_feature_id),
            'campaign_id': random.randint(1, self.max_campaign_id),
            'conversion_type': conv_type,
            'conversion_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'plan_from': plan_from,
            'plan_to': plan_to,
            'revenue': revenue,
            'properties': '{"source":"app"}'
        }
        return conversion

    def insert_event(self, event: dict):
        """Insert event into database."""
        self.execute(
            """INSERT INTO fact_events VALUES
               (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (event['event_id'], event['user_id'], event['feature_id'], event['campaign_id'],
             event['session_id'], event['event_type'], event['event_time'], event['page_url'],
             event['search_query'], event['properties'])
        )

    def insert_conversion(self, conversion: dict):
        """Insert conversion into database."""
        self.execute(
            """INSERT INTO fact_conversions VALUES
               (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (conversion['conversion_id'], conversion['user_id'], conversion['feature_id'],
             conversion['campaign_id'], conversion['conversion_type'], conversion['conversion_time'],
             conversion['plan_from'], conversion['plan_to'], conversion['revenue'], conversion['properties'])
        )

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
        props = f'{{"device":"{random.choice(DEVICES)}","browser":"{random.choice(BROWSERS)}"}}'

        self.execute(
            "INSERT INTO dim_users VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (i, email, name, signup_date, plan, country, industry, props)
        )
        print(f"[NEW USER] {name} ({email}) joined with {plan} plan")

    def run(self, events_per_second: float = 10, conversion_interval: float = 5, new_user_interval: float = 30):
        """Run continuous data generation."""
        print(f"[INFO] Starting data generation - {events_per_second} events/sec, "
              f"conversion every {conversion_interval}s, new user every {new_user_interval}s")

        event_interval = 1.0 / events_per_second
        last_conversion = time.time()
        last_new_user = time.time()
        events_generated = 0
        conversions_generated = 0

        while self.running:
            # Generate events
            event = self.generate_event()
            self.insert_event(event)
            events_generated += 1

            # Generate conversion periodically
            if time.time() - last_conversion >= conversion_interval:
                conversion = self.generate_conversion()
                self.insert_conversion(conversion)
                conversions_generated += 1
                last_conversion = time.time()
                print(f"[CONVERSION] {conversion['conversion_type']} - ${conversion['revenue']:.2f}")

            # Add new user periodically
            if time.time() - last_new_user >= new_user_interval:
                self.add_new_user()
                last_new_user = time.time()

            # Status update every 100 events
            if events_generated % 100 == 0:
                print(f"[STATUS] Events: {events_generated}, Conversions: {conversions_generated}, "
                      f"Users: {self.max_user_id}")

            time.sleep(event_interval)

        print(f"[INFO] Final stats - Events: {events_generated}, Conversions: {conversions_generated}")


def main():
    parser = argparse.ArgumentParser(description='VeloDB User Behavior Data Generator (Continuous Mode)')
    parser.add_argument('--host', default='localhost', help='Database host')
    parser.add_argument('--port', type=int, default=9030, help='Database port')
    parser.add_argument('--user', default='root', help='Database user')
    parser.add_argument('--password', default='', help='Database password')
    parser.add_argument('--database', default='user_analytics', help='Database name')
    parser.add_argument('--events-per-second', type=float, default=10, help='Events to generate per second')
    parser.add_argument('--conversion-interval', type=float, default=5, help='Seconds between conversions')
    parser.add_argument('--new-user-interval', type=float, default=30, help='Seconds between new users')

    args = parser.parse_args()

    gen = DataGenerator(args.host, args.port, args.user, args.password, args.database)

    if not gen.connect():
        sys.exit(1)

    try:
        if not gen.get_max_ids():
            sys.exit(1)
        gen.run(args.events_per_second, args.conversion_interval, args.new_user_interval)
    finally:
        gen.disconnect()


if __name__ == '__main__':
    main()
