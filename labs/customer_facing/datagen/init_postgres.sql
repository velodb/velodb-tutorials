-- Initialize PostgreSQL database with CDC-enabled tables
-- This matches the 5-table star schema for user analytics
-- All tables are synced via Flink CDC to VeloDB

-- =============================================
-- DIMENSION TABLES
-- =============================================

-- Users dimension table
CREATE TABLE IF NOT EXISTS dim_users (
    user_id SERIAL PRIMARY KEY,
    email VARCHAR(200) NOT NULL UNIQUE,
    name VARCHAR(100),
    signup_date DATE DEFAULT CURRENT_DATE,
    plan VARCHAR(20) DEFAULT 'Free',
    country VARCHAR(50),
    industry VARCHAR(50),
    properties JSONB
);

-- Features dimension table
CREATE TABLE IF NOT EXISTS dim_features (
    feature_id SERIAL PRIMARY KEY,
    feature_name VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    description TEXT,
    tier_required VARCHAR(20) DEFAULT 'Free'
);

-- Campaigns dimension table
CREATE TABLE IF NOT EXISTS dim_campaigns (
    campaign_id SERIAL PRIMARY KEY,
    campaign_name VARCHAR(100),
    channel VARCHAR(50),
    source VARCHAR(50),
    medium VARCHAR(50)
);

-- =============================================
-- FACT TABLES
-- =============================================

-- Fact Events table (user behavior events)
CREATE TABLE IF NOT EXISTS fact_events (
    event_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES dim_users(user_id),
    feature_id INT REFERENCES dim_features(feature_id),
    campaign_id INT REFERENCES dim_campaigns(campaign_id),
    session_id VARCHAR(50),
    event_type VARCHAR(50),
    event_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    page_url VARCHAR(500),
    search_query VARCHAR(200),
    properties JSONB
);

-- Fact Conversions table (revenue events)
CREATE TABLE IF NOT EXISTS fact_conversions (
    conversion_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES dim_users(user_id),
    feature_id INT REFERENCES dim_features(feature_id),
    campaign_id INT REFERENCES dim_campaigns(campaign_id),
    conversion_type VARCHAR(50),
    conversion_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    plan_from VARCHAR(20),
    plan_to VARCHAR(20),
    revenue DECIMAL(10,2),
    properties JSONB
);

-- Enable REPLICA IDENTITY FULL for CDC to capture DELETE operations
ALTER TABLE dim_users REPLICA IDENTITY FULL;
ALTER TABLE dim_features REPLICA IDENTITY FULL;
ALTER TABLE dim_campaigns REPLICA IDENTITY FULL;
ALTER TABLE fact_events REPLICA IDENTITY FULL;
ALTER TABLE fact_conversions REPLICA IDENTITY FULL;

-- Create indexes for better query performance
CREATE INDEX idx_fact_events_user ON fact_events(user_id);
CREATE INDEX idx_fact_events_time ON fact_events(event_time);
CREATE INDEX idx_fact_conversions_user ON fact_conversions(user_id);
CREATE INDEX idx_fact_conversions_time ON fact_conversions(conversion_time);

-- Create replication user (for CDC)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'replication_user') THEN
        CREATE ROLE replication_user WITH REPLICATION LOGIN PASSWORD 'replication_pass';
    END IF;
END
$$;

-- Grant permissions
GRANT SELECT ON ALL TABLES IN SCHEMA public TO replication_user;
GRANT USAGE ON SCHEMA public TO replication_user;

-- Seed Users (10 initial users across different plans)
INSERT INTO dim_users (email, name, signup_date, plan, country, industry) VALUES
    ('alex.chen@company.com', 'Alex Chen', '2024-01-15', 'Enterprise', 'USA', 'Technology'),
    ('sam.smith@startup.io', 'Sam Smith', '2024-01-20', 'Pro', 'UK', 'Finance'),
    ('jordan.garcia@gmail.com', 'Jordan Garcia', '2024-02-01', 'Free', 'Germany', 'Healthcare'),
    ('taylor.kim@outlook.com', 'Taylor Kim', '2024-02-10', 'Pro', 'Japan', 'Retail'),
    ('morgan.patel@tech.co', 'Morgan Patel', '2024-02-15', 'Enterprise', 'India', 'Technology'),
    ('casey.mueller@company.com', 'Casey Mueller', '2024-03-01', 'Free', 'Germany', 'Education'),
    ('riley.santos@startup.io', 'Riley Santos', '2024-03-10', 'Pro', 'Brazil', 'Finance'),
    ('quinn.nguyen@gmail.com', 'Quinn Nguyen', '2024-03-15', 'Free', 'USA', 'Healthcare'),
    ('avery.johnson@outlook.com', 'Avery Johnson', '2024-03-20', 'Enterprise', 'Canada', 'Manufacturing'),
    ('blake.lee@tech.co', 'Blake Lee', '2024-04-01', 'Pro', 'Australia', 'Technology')
ON CONFLICT (email) DO NOTHING;

-- Seed Features (10 product features across tiers)
INSERT INTO dim_features (feature_name, category, description, tier_required) VALUES
    ('Analytics Builder', 'Analytics', 'Create custom analytics dashboards', 'Free'),
    ('Analytics Manager', 'Analytics', 'Manage and organize analytics', 'Pro'),
    ('Dashboard Viewer', 'Visualization', 'View shared dashboards', 'Free'),
    ('Export Manager', 'Data', 'Export data to various formats', 'Pro'),
    ('Report Builder', 'Reporting', 'Build custom reports', 'Pro'),
    ('Integration Console', 'Integration', 'Connect external data sources', 'Enterprise'),
    ('Analytics Dashboard', 'Analytics', 'Pre-built analytics views', 'Free'),
    ('Data Pipeline', 'Data', 'Automated data workflows', 'Enterprise'),
    ('User Segments', 'Analytics', 'Create user cohorts', 'Pro'),
    ('Custom Metrics', 'Analytics', 'Define custom KPIs', 'Enterprise')
ON CONFLICT DO NOTHING;

-- Seed Campaigns (5 marketing channels)
INSERT INTO dim_campaigns (campaign_name, channel, source, medium) VALUES
    ('Organic Search', 'Organic', 'google', 'organic'),
    ('Paid Search', 'Paid', 'google', 'cpc'),
    ('Social Media', 'Social', 'linkedin', 'social'),
    ('Email Newsletter', 'Email', 'newsletter', 'email'),
    ('Direct Traffic', 'Direct', 'direct', 'none')
ON CONFLICT DO NOTHING;
