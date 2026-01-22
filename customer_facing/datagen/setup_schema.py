#!/usr/bin/env python3
"""
Create database and schema for VeloDB Customer Analytics Demo.
Run this FIRST before seeding data.
"""

import argparse
import mysql.connector
from mysql.connector import Error

SCHEMA_SQL = """
-- Create database if not exists
CREATE DATABASE IF NOT EXISTS {database};

USE {database};

-- Dimension: Users
CREATE TABLE IF NOT EXISTS dim_users (
    user_id BIGINT,
    email VARCHAR(200),
    name VARCHAR(100),
    signup_date DATE,
    plan VARCHAR(20),
    country VARCHAR(50),
    industry VARCHAR(50),
    properties VARIANT
)
DUPLICATE KEY(user_id)
DISTRIBUTED BY HASH(user_id) BUCKETS 4
PROPERTIES("replication_num" = "1");

-- Dimension: Features
CREATE TABLE IF NOT EXISTS dim_features (
    feature_id BIGINT,
    feature_name VARCHAR(100),
    category VARCHAR(50),
    description TEXT,
    tier_required VARCHAR(20),
    INDEX idx_feature_desc (description) USING INVERTED PROPERTIES("parser" = "english")
)
DUPLICATE KEY(feature_id)
DISTRIBUTED BY HASH(feature_id) BUCKETS 4
PROPERTIES("replication_num" = "1");

-- Dimension: Campaigns
CREATE TABLE IF NOT EXISTS dim_campaigns (
    campaign_id BIGINT,
    campaign_name VARCHAR(100),
    channel VARCHAR(50),
    source VARCHAR(50),
    medium VARCHAR(50),
    properties VARIANT
)
DUPLICATE KEY(campaign_id)
DISTRIBUTED BY HASH(campaign_id) BUCKETS 4
PROPERTIES("replication_num" = "1");

-- Fact: Events
CREATE TABLE IF NOT EXISTS fact_events (
    event_id BIGINT,
    user_id BIGINT,
    feature_id BIGINT,
    campaign_id BIGINT,
    session_id VARCHAR(50),
    event_type VARCHAR(50),
    event_time DATETIME,
    page_url VARCHAR(500),
    search_query VARCHAR(200),
    properties VARIANT,
    INDEX idx_search (search_query) USING INVERTED PROPERTIES("parser" = "english")
)
DUPLICATE KEY(event_id)
DISTRIBUTED BY HASH(event_id) BUCKETS 8
PROPERTIES("replication_num" = "1");

-- Fact: Conversions
CREATE TABLE IF NOT EXISTS fact_conversions (
    conversion_id BIGINT,
    user_id BIGINT,
    feature_id BIGINT,
    campaign_id BIGINT,
    conversion_type VARCHAR(50),
    conversion_time DATETIME,
    plan_from VARCHAR(20),
    plan_to VARCHAR(20),
    revenue DECIMAL(10,2),
    properties VARIANT
)
DUPLICATE KEY(conversion_id)
DISTRIBUTED BY HASH(conversion_id) BUCKETS 4
PROPERTIES("replication_num" = "1");
"""

SEED_USERS = """INSERT INTO dim_users VALUES
(1, 'alex.chen@gmail.com', 'Alex Chen', '2024-01-15', 'Pro', 'USA', 'Technology', '{"device":"desktop","browser":"Chrome"}'),
(2, 'sam.smith@company.com', 'Sam Smith', '2024-02-01', 'Enterprise', 'UK', 'Finance', '{"device":"desktop","browser":"Safari"}'),
(3, 'jordan.garcia@outlook.com', 'Jordan Garcia', '2024-02-15', 'Free', 'Germany', 'Healthcare', '{"device":"mobile","browser":"Chrome"}'),
(4, 'taylor.kim@startup.io', 'Taylor Kim', '2024-03-01', 'Pro', 'Japan', 'Technology', '{"device":"desktop","browser":"Firefox"}'),
(5, 'morgan.patel@tech.co', 'Morgan Patel', '2024-03-15', 'Free', 'India', 'Education', '{"device":"tablet","browser":"Safari"}'),
(6, 'casey.mueller@gmail.com', 'Casey Mueller', '2024-04-01', 'Enterprise', 'Germany', 'Manufacturing', '{"device":"desktop","browser":"Edge"}'),
(7, 'riley.santos@company.com', 'Riley Santos', '2024-04-15', 'Pro', 'Brazil', 'Retail', '{"device":"mobile","browser":"Chrome"}'),
(8, 'quinn.nguyen@outlook.com', 'Quinn Nguyen', '2024-05-01', 'Free', 'USA', 'Technology', '{"device":"desktop","browser":"Chrome"}'),
(9, 'avery.johnson@startup.io', 'Avery Johnson', '2024-05-15', 'Pro', 'Canada', 'Finance', '{"device":"desktop","browser":"Safari"}'),
(10, 'blake.lee@tech.co', 'Blake Lee', '2024-06-01', 'Enterprise', 'Australia', 'Healthcare', '{"device":"tablet","browser":"Firefox"}')"""

SEED_FEATURES = """INSERT INTO dim_features VALUES
(1, 'Analytics Dashboard', 'Core', 'Real-time analytics dashboard with customizable widgets', 'Free'),
(2, 'Report Builder', 'Core', 'Create custom reports with drag-and-drop interface', 'Free'),
(3, 'Export Manager', 'Core', 'Export data to CSV, Excel, and PDF formats', 'Pro'),
(4, 'Integration Console', 'Advanced', 'Connect to third-party services and APIs', 'Pro'),
(5, 'Dashboard Editor', 'Advanced', 'Advanced dashboard customization with code editor', 'Enterprise'),
(6, 'Report Viewer', 'Core', 'View and share pre-built reports', 'Free'),
(7, 'Analytics Builder', 'Advanced', 'Build complex analytics with SQL support', 'Pro'),
(8, 'Export Console', 'Advanced', 'Bulk export and scheduling capabilities', 'Enterprise'),
(9, 'Integration Manager', 'Beta', 'Manage all integrations in one place', 'Enterprise'),
(10, 'Dashboard Viewer', 'Core', 'View shared dashboards from team members', 'Free')"""

SEED_CAMPAIGNS = """INSERT INTO dim_campaigns VALUES
(1, 'Summer 2024 Campaign', 'Organic', 'Google', 'organic', '{"budget":5000,"target":"acquisition"}'),
(2, 'Launch Q1 Campaign', 'Paid', 'Facebook', 'cpc', '{"budget":10000,"target":"acquisition"}'),
(3, 'Growth Q2 Campaign', 'Social', 'LinkedIn', 'referral', '{"budget":7500,"target":"engagement"}'),
(4, 'Retarget Holiday Campaign', 'Email', 'Newsletter', 'email', '{"budget":3000,"target":"retention"}'),
(5, 'Brand 2025 Campaign', 'Direct', 'ProductHunt', 'referral', '{"budget":2000,"target":"awareness"}')"""


def setup_schema(host, port, user, password, database):
    """Create database and tables."""
    print("=" * 60)
    print("VeloDB Analytics - Schema Setup")
    print("=" * 60)

    try:
        # Connect without database first to create it
        conn = mysql.connector.connect(
            host=host, port=port, user=user, password=password, autocommit=True
        )
        cursor = conn.cursor()
        print(f"[INFO] Connected to {host}:{port}")

        # Execute schema SQL
        print(f"[INFO] Creating database '{database}' and tables...")
        for statement in SCHEMA_SQL.format(database=database).split(';'):
            statement = statement.strip()
            if statement:
                try:
                    cursor.execute(statement)
                except Error as e:
                    if "already exists" not in str(e).lower():
                        print(f"[WARN] {e}")
        print("[INFO] Schema created successfully")

        # Check if dimensions need seeding
        cursor.execute(f"SELECT COUNT(*) FROM {database}.dim_users")
        user_count = cursor.fetchone()[0]

        if user_count == 0:
            print("[INFO] Seeding dimension tables...")
            cursor.execute(f"USE {database}")
            try:
                cursor.execute(SEED_USERS)
                print("[INFO] Seeded dim_users")
                cursor.execute(SEED_FEATURES)
                print("[INFO] Seeded dim_features")
                cursor.execute(SEED_CAMPAIGNS)
                print("[INFO] Seeded dim_campaigns")
            except Error as e:
                print(f"[ERROR] Seed error: {e}")
            # Verify seeding worked
            cursor.execute("SELECT COUNT(*) FROM dim_users")
            cnt = cursor.fetchone()[0]
            print(f"[INFO] Dimension tables seeded ({cnt} users)")
        else:
            print(f"[INFO] Dimension tables already have data ({user_count} users)")

        cursor.close()
        conn.close()
        return True

    except Error as e:
        print(f"[ERROR] Setup failed: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Setup VeloDB Analytics Schema")
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, default=9030)
    parser.add_argument("--user", required=True)
    parser.add_argument("--password", default="")
    parser.add_argument("--database", default="user_analytics")

    args = parser.parse_args()
    success = setup_schema(args.host, args.port, args.user, args.password, args.database)
    exit(0 if success else 1)
