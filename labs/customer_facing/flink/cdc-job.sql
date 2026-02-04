-- Flink CDC Job: PostgreSQL -> VeloDB
-- Syncs all 5 tables in the user_analytics star schema

-- =============================================
-- EXECUTION CONFIGURATION
-- =============================================
SET 'execution.checkpointing.interval' = '10s';
SET 'execution.checkpointing.mode' = 'EXACTLY_ONCE';
SET 'execution.checkpointing.timeout' = '60s';

-- =============================================
-- SOURCE: PostgreSQL CDC Tables
-- =============================================

-- dim_users source
CREATE TABLE pg_dim_users (
    user_id INT,
    email STRING,
    name STRING,
    signup_date DATE,
    plan STRING,
    country STRING,
    industry STRING,
    properties STRING,
    PRIMARY KEY (user_id) NOT ENFORCED
) WITH (
    'connector' = 'postgres-cdc',
    'hostname' = '${POSTGRES_HOST}',
    'port' = '${POSTGRES_PORT}',
    'username' = '${POSTGRES_USER}',
    'password' = '${POSTGRES_PASSWORD}',
    'database-name' = '${POSTGRES_DB}',
    'schema-name' = 'public',
    'table-name' = 'dim_users',
    'slot.name' = 'flink_dim_users_slot',
    'decoding.plugin.name' = 'pgoutput'
);

-- dim_features source
CREATE TABLE pg_dim_features (
    feature_id INT,
    feature_name STRING,
    category STRING,
    description STRING,
    tier_required STRING,
    PRIMARY KEY (feature_id) NOT ENFORCED
) WITH (
    'connector' = 'postgres-cdc',
    'hostname' = '${POSTGRES_HOST}',
    'port' = '${POSTGRES_PORT}',
    'username' = '${POSTGRES_USER}',
    'password' = '${POSTGRES_PASSWORD}',
    'database-name' = '${POSTGRES_DB}',
    'schema-name' = 'public',
    'table-name' = 'dim_features',
    'slot.name' = 'flink_dim_features_slot',
    'decoding.plugin.name' = 'pgoutput'
);

-- dim_campaigns source
CREATE TABLE pg_dim_campaigns (
    campaign_id INT,
    campaign_name STRING,
    channel STRING,
    source STRING,
    medium STRING,
    PRIMARY KEY (campaign_id) NOT ENFORCED
) WITH (
    'connector' = 'postgres-cdc',
    'hostname' = '${POSTGRES_HOST}',
    'port' = '${POSTGRES_PORT}',
    'username' = '${POSTGRES_USER}',
    'password' = '${POSTGRES_PASSWORD}',
    'database-name' = '${POSTGRES_DB}',
    'schema-name' = 'public',
    'table-name' = 'dim_campaigns',
    'slot.name' = 'flink_dim_campaigns_slot',
    'decoding.plugin.name' = 'pgoutput'
);

-- fact_events source
CREATE TABLE pg_fact_events (
    event_id INT,
    user_id INT,
    feature_id INT,
    campaign_id INT,
    session_id STRING,
    event_type STRING,
    event_time TIMESTAMP(3),
    page_url STRING,
    search_query STRING,
    properties STRING,
    PRIMARY KEY (event_id) NOT ENFORCED
) WITH (
    'connector' = 'postgres-cdc',
    'hostname' = '${POSTGRES_HOST}',
    'port' = '${POSTGRES_PORT}',
    'username' = '${POSTGRES_USER}',
    'password' = '${POSTGRES_PASSWORD}',
    'database-name' = '${POSTGRES_DB}',
    'schema-name' = 'public',
    'table-name' = 'fact_events',
    'slot.name' = 'flink_fact_events_slot',
    'decoding.plugin.name' = 'pgoutput'
);

-- fact_conversions source
CREATE TABLE pg_fact_conversions (
    conversion_id INT,
    user_id INT,
    feature_id INT,
    campaign_id INT,
    conversion_type STRING,
    conversion_time TIMESTAMP(3),
    plan_from STRING,
    plan_to STRING,
    revenue DECIMAL(10,2),
    properties STRING,
    PRIMARY KEY (conversion_id) NOT ENFORCED
) WITH (
    'connector' = 'postgres-cdc',
    'hostname' = '${POSTGRES_HOST}',
    'port' = '${POSTGRES_PORT}',
    'username' = '${POSTGRES_USER}',
    'password' = '${POSTGRES_PASSWORD}',
    'database-name' = '${POSTGRES_DB}',
    'schema-name' = 'public',
    'table-name' = 'fact_conversions',
    'slot.name' = 'flink_fact_conversions_slot',
    'decoding.plugin.name' = 'pgoutput'
);

-- =============================================
-- SINK: VeloDB/Doris Tables
-- =============================================

-- dim_users sink
CREATE TABLE velodb_dim_users (
    user_id INT,
    email STRING,
    name STRING,
    signup_date DATE,
    plan STRING,
    country STRING,
    industry STRING,
    properties STRING,
    PRIMARY KEY (user_id) NOT ENFORCED
) WITH (
    'connector' = 'doris',
    'fenodes' = '${VELODB_FE_HOST}:${VELODB_HTTP_PORT}',
    'table.identifier' = '${VELODB_DATABASE}.dim_users',
    'username' = '${VELODB_USER}',
    'password' = '${VELODB_PASSWORD}',
    'sink.enable-2pc' = 'false',
    'sink.label-prefix' = 'flink_dim_users'
);

-- dim_features sink
CREATE TABLE velodb_dim_features (
    feature_id INT,
    feature_name STRING,
    category STRING,
    description STRING,
    tier_required STRING,
    PRIMARY KEY (feature_id) NOT ENFORCED
) WITH (
    'connector' = 'doris',
    'fenodes' = '${VELODB_FE_HOST}:${VELODB_HTTP_PORT}',
    'table.identifier' = '${VELODB_DATABASE}.dim_features',
    'username' = '${VELODB_USER}',
    'password' = '${VELODB_PASSWORD}',
    'sink.enable-2pc' = 'false',
    'sink.label-prefix' = 'flink_dim_features'
);

-- dim_campaigns sink
CREATE TABLE velodb_dim_campaigns (
    campaign_id INT,
    campaign_name STRING,
    channel STRING,
    source STRING,
    medium STRING,
    PRIMARY KEY (campaign_id) NOT ENFORCED
) WITH (
    'connector' = 'doris',
    'fenodes' = '${VELODB_FE_HOST}:${VELODB_HTTP_PORT}',
    'table.identifier' = '${VELODB_DATABASE}.dim_campaigns',
    'username' = '${VELODB_USER}',
    'password' = '${VELODB_PASSWORD}',
    'sink.enable-2pc' = 'false',
    'sink.label-prefix' = 'flink_dim_campaigns'
);

-- fact_events sink
CREATE TABLE velodb_fact_events (
    event_id INT,
    user_id INT,
    feature_id INT,
    campaign_id INT,
    session_id STRING,
    event_type STRING,
    event_time TIMESTAMP(3),
    page_url STRING,
    search_query STRING,
    properties STRING,
    PRIMARY KEY (event_id) NOT ENFORCED
) WITH (
    'connector' = 'doris',
    'fenodes' = '${VELODB_FE_HOST}:${VELODB_HTTP_PORT}',
    'table.identifier' = '${VELODB_DATABASE}.fact_events',
    'username' = '${VELODB_USER}',
    'password' = '${VELODB_PASSWORD}',
    'sink.enable-2pc' = 'false',
    'sink.label-prefix' = 'flink_fact_events'
);

-- fact_conversions sink
CREATE TABLE velodb_fact_conversions (
    conversion_id INT,
    user_id INT,
    feature_id INT,
    campaign_id INT,
    conversion_type STRING,
    conversion_time TIMESTAMP(3),
    plan_from STRING,
    plan_to STRING,
    revenue DECIMAL(10,2),
    properties STRING,
    PRIMARY KEY (conversion_id) NOT ENFORCED
) WITH (
    'connector' = 'doris',
    'fenodes' = '${VELODB_FE_HOST}:${VELODB_HTTP_PORT}',
    'table.identifier' = '${VELODB_DATABASE}.fact_conversions',
    'username' = '${VELODB_USER}',
    'password' = '${VELODB_PASSWORD}',
    'sink.enable-2pc' = 'false',
    'sink.label-prefix' = 'flink_fact_conversions'
);

-- =============================================
-- SYNC JOBS: Insert from source to sink
-- =============================================

INSERT INTO velodb_dim_users SELECT * FROM pg_dim_users;
INSERT INTO velodb_dim_features SELECT * FROM pg_dim_features;
INSERT INTO velodb_dim_campaigns SELECT * FROM pg_dim_campaigns;
INSERT INTO velodb_fact_events SELECT * FROM pg_fact_events;
INSERT INTO velodb_fact_conversions SELECT * FROM pg_fact_conversions;
