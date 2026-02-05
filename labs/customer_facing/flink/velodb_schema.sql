-- VeloDB Target Schema for Integration Lab
-- Run this in VeloDB SQL Editor before starting the CDC job
-- All 5 tables are synced via Flink CDC from PostgreSQL

CREATE DATABASE IF NOT EXISTS user_analytics;
USE user_analytics;

-- =============================================
-- DIMENSION TABLES
-- =============================================

-- Users dimension table
CREATE TABLE IF NOT EXISTS dim_users (
    user_id BIGINT,
    email VARCHAR(200),
    name VARCHAR(100),
    signup_date DATE,
    plan VARCHAR(20),
    country VARCHAR(50),
    industry VARCHAR(50),
    properties VARCHAR(65533)
)
UNIQUE KEY(user_id)
DISTRIBUTED BY HASH(user_id) BUCKETS 4
PROPERTIES (
    "replication_num" = "1",
    "enable_unique_key_merge_on_write" = "true"
);

-- Features dimension table
CREATE TABLE IF NOT EXISTS dim_features (
    feature_id BIGINT,
    feature_name VARCHAR(100),
    category VARCHAR(50),
    description TEXT,
    tier_required VARCHAR(20)
)
UNIQUE KEY(feature_id)
DISTRIBUTED BY HASH(feature_id) BUCKETS 4
PROPERTIES (
    "replication_num" = "1",
    "enable_unique_key_merge_on_write" = "true"
);

-- Campaigns dimension table
CREATE TABLE IF NOT EXISTS dim_campaigns (
    campaign_id BIGINT,
    campaign_name VARCHAR(100),
    channel VARCHAR(50),
    source VARCHAR(50),
    medium VARCHAR(50)
)
UNIQUE KEY(campaign_id)
DISTRIBUTED BY HASH(campaign_id) BUCKETS 4
PROPERTIES (
    "replication_num" = "1",
    "enable_unique_key_merge_on_write" = "true"
);

-- =============================================
-- FACT TABLES
-- =============================================

-- Fact Events table (user behavior events)
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
    properties VARCHAR(65533)
)
UNIQUE KEY(event_id)
DISTRIBUTED BY HASH(user_id) BUCKETS 4
PROPERTIES (
    "replication_num" = "1",
    "enable_unique_key_merge_on_write" = "true"
);

-- Fact Conversions table (revenue events)
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
    properties VARCHAR(65533)
)
UNIQUE KEY(conversion_id)
DISTRIBUTED BY HASH(user_id) BUCKETS 4
PROPERTIES (
    "replication_num" = "1",
    "enable_unique_key_merge_on_write" = "true"
);

-- =============================================
-- KAFKA SINK TABLE (for Kafka -> VeloDB path)
-- =============================================

-- Kafka events table (separate from Flink CDC to avoid duplicates)
-- This demonstrates the Kafka Connect -> VeloDB path
-- Note: merge-on-write must be disabled for Kafka Connect 2PC compatibility
CREATE TABLE IF NOT EXISTS kafka_fact_events (
    event_id BIGINT,
    user_id BIGINT,
    feature_id BIGINT,
    campaign_id BIGINT,
    session_id VARCHAR(50),
    event_type VARCHAR(50),
    event_time DATETIME,
    page_url VARCHAR(500),
    search_query VARCHAR(200),
    properties VARCHAR(65533)
)
UNIQUE KEY(event_id)
DISTRIBUTED BY HASH(event_id) BUCKETS 4
PROPERTIES (
    "replication_num" = "1",
    "enable_unique_key_merge_on_write" = "false"
);

-- =============================================
-- INDEXES
-- =============================================

CREATE INDEX IF NOT EXISTS idx_event_type ON fact_events(event_type) USING INVERTED;
CREATE INDEX IF NOT EXISTS idx_event_time ON fact_events(event_time) USING INVERTED;
CREATE INDEX IF NOT EXISTS idx_conversion_type ON fact_conversions(conversion_type) USING INVERTED;
CREATE INDEX IF NOT EXISTS idx_conversion_time ON fact_conversions(conversion_time) USING INVERTED;

-- =============================================
-- VERIFICATION
-- =============================================

SHOW TABLES;

-- Check table structure
DESC dim_users;
DESC dim_features;
DESC dim_campaigns;
DESC fact_events;
DESC fact_conversions;
