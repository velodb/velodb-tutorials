#!/usr/bin/env python3
"""
Seed 30 days of historical data for presentable dashboard charts.
Run this ONCE before starting the continuous datagen.

Creates realistic patterns:
- Weekday vs weekend variation (higher on weekdays)
- Hourly variation (peak during business hours)
- Growth trend (gradual increase over 30 days)
"""

import argparse
import random
import sys
from datetime import datetime, timedelta
import mysql.connector
from mysql.connector import Error

# Configuration
PLANS = ['Free', 'Pro', 'Enterprise']
COUNTRIES = ['USA', 'UK', 'Germany', 'Japan', 'Brazil', 'India', 'Canada', 'Australia']
INDUSTRIES = ['Technology', 'Finance', 'Healthcare', 'Retail', 'Education', 'Manufacturing']

EVENT_TYPES = ['page_view', 'feature_use', 'search', 'click', 'scroll', 'form_start', 'form_submit', 'error']
PAGES = ['/app/dashboard', '/app/analytics', '/app/settings', '/app/reports', '/app/integrations']
SEARCH_QUERIES = ['how to dashboard', 'create report', 'export data', 'analyze users', 'integrate api', 'build chart']
CONVERSION_TYPES = ['signup', 'upgrade', 'purchase', 'churn']


def get_hourly_multiplier(hour: int) -> float:
    """Return activity multiplier based on hour (business hours = higher)."""
    if 9 <= hour <= 17:  # Business hours
        return 1.5
    elif 6 <= hour <= 21:  # Active hours
        return 1.0
    else:  # Night
        return 0.3


def get_weekday_multiplier(weekday: int) -> float:
    """Return activity multiplier (Mon=0, Sun=6)."""
    if weekday < 5:  # Weekday
        return 1.0
    else:  # Weekend
        return 0.5


def get_growth_multiplier(days_ago: int) -> float:
    """Return growth multiplier (older = less activity, showing growth trend)."""
    # 30 days ago = 0.6x, today = 1.0x (40% growth over month)
    return 0.6 + (0.4 * (30 - days_ago) / 30)


def seed_historical_data(host, port, user, password, database, days=30):
    """Seed historical events and conversions."""

    print("=" * 60)
    print("VeloDB Analytics - Historical Data Seeder")
    print("=" * 60)

    try:
        conn = mysql.connector.connect(
            host=host, port=port, user=user, password=password, database=database, autocommit=False
        )
        cursor = conn.cursor()
        print(f"[INFO] Connected to {host}:{port}/{database}")
    except Error as e:
        print(f"[ERROR] Connection failed: {e}")
        return False

    # Get dimension counts
    cursor.execute("SELECT MAX(user_id) FROM dim_users")
    max_user_id = cursor.fetchone()[0] or 0
    cursor.execute("SELECT MAX(feature_id) FROM dim_features")
    max_feature_id = cursor.fetchone()[0] or 0
    cursor.execute("SELECT MAX(campaign_id) FROM dim_campaigns")
    max_campaign_id = cursor.fetchone()[0] or 0

    if max_user_id == 0 or max_feature_id == 0 or max_campaign_id == 0:
        print("[ERROR] Dimension tables are empty. Run tutorial SQL to create schema first.")
        return False

    print(f"[INFO] Found {max_user_id} users, {max_feature_id} features, {max_campaign_id} campaigns")

    # Get current max IDs for fact tables
    cursor.execute("SELECT COALESCE(MAX(event_id), 0) FROM fact_events")
    event_id = cursor.fetchone()[0]
    cursor.execute("SELECT COALESCE(MAX(conversion_id), 0) FROM fact_conversions")
    conversion_id = cursor.fetchone()[0]

    now = datetime.now()
    total_events = 0
    total_conversions = 0

    print(f"\n[INFO] Generating {days} days of historical data...")

    # Base rates (per hour)
    BASE_EVENTS_PER_HOUR = 50
    BASE_CONVERSIONS_PER_HOUR = 3

    events_batch = []
    conversions_batch = []
    BATCH_SIZE = 1000

    for days_ago in range(days, 0, -1):
        day = now - timedelta(days=days_ago)
        weekday = day.weekday()
        weekday_mult = get_weekday_multiplier(weekday)
        growth_mult = get_growth_multiplier(days_ago)

        for hour in range(24):
            hourly_mult = get_hourly_multiplier(hour)

            # Calculate events for this hour
            events_this_hour = int(BASE_EVENTS_PER_HOUR * hourly_mult * weekday_mult * growth_mult)
            conversions_this_hour = int(BASE_CONVERSIONS_PER_HOUR * hourly_mult * weekday_mult * growth_mult)

            # Add some randomness
            events_this_hour = max(1, events_this_hour + random.randint(-5, 5))
            conversions_this_hour = max(0, conversions_this_hour + random.randint(-1, 1))

            for _ in range(events_this_hour):
                event_id += 1
                event_time = day.replace(hour=hour, minute=random.randint(0, 59), second=random.randint(0, 59))

                events_batch.append((
                    event_id,
                    random.randint(1, max_user_id),
                    random.randint(1, max_feature_id),
                    random.randint(1, max_campaign_id),
                    f"sess_{random.randint(1, 100000)}",
                    random.choice(EVENT_TYPES),
                    event_time.strftime('%Y-%m-%d %H:%M:%S'),
                    random.choice(PAGES),
                    random.choice(SEARCH_QUERIES) if random.random() < 0.15 else None,
                    f'{{"duration":{random.randint(1, 300)}}}'
                ))
                total_events += 1

                if len(events_batch) >= BATCH_SIZE:
                    cursor.executemany(
                        "INSERT INTO fact_events VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                        events_batch
                    )
                    conn.commit()
                    events_batch = []

            for _ in range(conversions_this_hour):
                conversion_id += 1
                conv_type = random.choice(CONVERSION_TYPES)
                conv_time = day.replace(hour=hour, minute=random.randint(0, 59), second=random.randint(0, 59))

                plan_from = random.choice([None, 'Free', 'Pro']) if conv_type != 'signup' else None
                plan_to = random.choice(['Pro', 'Enterprise']) if conv_type in ['signup', 'upgrade'] else None
                revenue = round(random.uniform(10, 500) if random.random() < 0.7 else random.uniform(500, 2000), 2)

                conversions_batch.append((
                    conversion_id,
                    random.randint(1, max_user_id),
                    random.randint(1, max_feature_id),
                    random.randint(1, max_campaign_id),
                    conv_type,
                    conv_time.strftime('%Y-%m-%d %H:%M:%S'),
                    plan_from,
                    plan_to,
                    revenue,
                    '{"source":"app"}'
                ))
                total_conversions += 1

                if len(conversions_batch) >= BATCH_SIZE:
                    cursor.executemany(
                        "INSERT INTO fact_conversions VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                        conversions_batch
                    )
                    conn.commit()
                    conversions_batch = []

        # Progress indicator
        if days_ago % 5 == 0:
            print(f"  Day -{days_ago}: {total_events} events, {total_conversions} conversions so far...")

    # Insert remaining batches
    if events_batch:
        cursor.executemany("INSERT INTO fact_events VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", events_batch)
    if conversions_batch:
        cursor.executemany("INSERT INTO fact_conversions VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", conversions_batch)
    conn.commit()

    cursor.close()
    conn.close()

    print("\n" + "=" * 60)
    print("Historical Data Seeding Complete!")
    print("=" * 60)
    print(f"  Events generated:      {total_events:,}")
    print(f"  Conversions generated: {total_conversions:,}")
    print(f"  Date range:            {(now - timedelta(days=days)).strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')}")
    print("=" * 60)

    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Seed historical data for VeloDB Analytics')
    parser.add_argument('--host', default='localhost', help='VeloDB host')
    parser.add_argument('--port', type=int, default=9030, help='VeloDB port')
    parser.add_argument('--user', default='root', help='Database user')
    parser.add_argument('--password', default='', help='Database password')
    parser.add_argument('--database', default='user_analytics', help='Database name')
    parser.add_argument('--days', type=int, default=30, help='Days of history to generate')

    args = parser.parse_args()

    success = seed_historical_data(
        args.host, args.port, args.user, args.password, args.database, args.days
    )
    sys.exit(0 if success else 1)
