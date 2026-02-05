# VeloDB Real-Time Data Integration Lab

A hands-on lab for system integrators demonstrating real-time data pipelines into VeloDB Cloud using PostgreSQL CDC, Kafka streaming, and Superset visualization.

**Duration**: ~2 hours
**Environment**: VeloDB Cloud (SaaS)
**Audience**: System Integrators, Data Engineers

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Prerequisites](#2-prerequisites)
3. [Environment Setup](#3-environment-setup)
4. [Module 1: PostgreSQL CDC with Flink](#4-module-1-postgresql-cdc-with-flink)
5. [Module 2: Kafka Integration](#5-module-2-kafka-integration)
6. [Module 3: Superset BI Dashboard](#6-module-3-superset-bi-dashboard)
7. [Module 4: End-to-End Verification](#7-module-4-end-to-end-verification)
8. [Troubleshooting](#8-troubleshooting)
9. [Cleanup](#9-cleanup)
10. [Appendix: Configuration Files](#10-appendix-configuration-files)

---

## Dashboard Preview

![VeloDB User Analytics Dashboard](./docs/user-analytics-1.png)

The final dashboard includes:
- **KPI Cards**: Active Users, Total Events, Sessions, Conversions, Revenue (30-day metrics)
- **Hourly Activity**: Real-time trend of events and users (24h)
- **Daily Activity**: Events, sessions, and users trend (30d)
- **Activity by Plan**: User activity segmented by subscription tier (Free/Pro/Enterprise)
- **Top 10 Features**: Most used product features
- **Feature Adoption Heatmap**: Feature usage across different plans

---

## 1. Architecture Overview

This lab demonstrates real-time data integration using a **5-table star schema** for user behavior analytics. All tables are stored in PostgreSQL and synced to VeloDB via **Flink CDC**.

### System Architecture

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                   DOCKER COMPOSE                                        │
│                                (Your Local Machine)                                     │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │ DATAGEN Container                                                                │   │
│  │ ┌───────────────────────────────────────────────────────────────────────────┐   │   │
│  │ │  continuous_datagen.py                                                     │   │   │
│  │ │  • Generates ~5 events/second                                              │   │   │
│  │ │  • New conversion every 5 seconds                                          │   │   │
│  │ │  • New user every 30 seconds                                               │   │   │
│  │ └───────────────────────────────────────────────────────────────────────────┘   │   │
│  └──────────────────────────────────────┬──────────────────────────────────────────┘   │
│                                         │ INSERT                                        │
│                                         ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │ POSTGRESQL Container (:5432)                                                     │   │
│  │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                                 │   │
│  │ │ dim_users   │ │dim_features │ │dim_campaigns│  ◄── Seed data on startup       │   │
│  │ │ (10 users)  │ │(10 features)│ │(5 campaigns)│                                 │   │
│  │ └─────────────┘ └─────────────┘ └─────────────┘                                 │   │
│  │ ┌─────────────────────┐ ┌─────────────────────┐                                 │   │
│  │ │    fact_events      │ │  fact_conversions   │  ◄── Continuous streaming data  │   │
│  │ │  (growing ~5/sec)   │ │  (growing ~1/5sec)  │                                 │   │
│  │ └─────────────────────┘ └─────────────────────┘                                 │   │
│  │                                                                                  │   │
│  │  [wal_level=logical] ──► WAL Logs (Change Data Capture)                         │   │
│  └──────────────────────────────────────┬──────────────────────────────────────────┘   │
│                                         │ CDC Stream                                    │
│                                         ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │ FLINK-CDC Container (:8081 Web UI)                                               │   │
│  │ ┌───────────────────────────────────────────────────────────────────────────┐   │   │
│  │ │  Flink SQL Client + CDC Connectors                                         │   │   │
│  │ │  • postgres-cdc-2.4.2: Reads WAL changes from PostgreSQL                   │   │   │
│  │ │  • flink-doris-connector-1.5.2: Writes to VeloDB/Doris                     │   │   │
│  │ │                                                                             │   │   │
│  │ │  5 streaming pipelines (one per table):                                     │   │   │
│  │ │  source_dim_users ────────► sink_dim_users                                  │   │   │
│  │ │  source_dim_features ─────► sink_dim_features                               │   │   │
│  │ │  source_dim_campaigns ────► sink_dim_campaigns                              │   │   │
│  │ │  source_fact_events ──────► sink_fact_events                                │   │   │
│  │ │  source_fact_conversions ─► sink_fact_conversions                           │   │   │
│  │ └───────────────────────────────────────────────────────────────────────────┘   │   │
│  └──────────────────────────────────────┬──────────────────────────────────────────┘   │
│                                         │ Stream Load (HTTP)                            │
└─────────────────────────────────────────┼──────────────────────────────────────────────┘
                                          │
                                          ▼
                     ┌──────────────────────────────────────────┐
                     │            VELODB CLOUD                   │
                     │         (user_analytics DB)               │
                     │                                           │
                     │  HTTP Port: 8080    Query Port: 9030      │
                     │                                           │
                     │  ┌─────────────┐ ┌─────────────┐         │
                     │  │ dim_users   │ │dim_features │         │
                     │  └─────────────┘ └─────────────┘         │
                     │  ┌─────────────┐ ┌─────────────────────┐ │
                     │  │dim_campaigns│ │    fact_events      │ │
                     │  └─────────────┘ └─────────────────────┘ │
                     │  ┌─────────────────────┐                 │
                     │  │  fact_conversions   │                 │
                     │  └─────────────────────┘                 │
                     │  (All tables: UNIQUE KEY + Merge-on-Write)│
                     └────────────────────┬─────────────────────┘
                                          │ MySQL Protocol (:9030)
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│  SUPERSET Container (:8088)                                                             │
│  ┌───────────────────────────────────────────────────────────────────────────────────┐ │
│  │  User Analytics Dashboard                                                          │ │
│  │  • KPI Cards: Active Users, Events, Sessions, Conversions, Revenue               │ │
│  │  • Charts: Hourly/Daily Activity, Activity by Plan, Top Features                  │ │
│  │  • Heatmap: Feature Adoption across Plans                                         │ │
│  └───────────────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────────────┘

Access Points:
  • PostgreSQL:      localhost:5432   (user: labuser / pass: labpass)
  • Flink Web UI:    http://localhost:8081
  • Superset:        http://localhost:8088  (user: admin / pass: admin)
  • VeloDB Cloud:    Your configured endpoint (:9030 for queries, :8080 for HTTP)
```

### Dual Data Paths (Both Enabled by Default)

This lab demonstrates **two parallel ingestion paths** to VeloDB:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DOCKER COMPOSE                                        │
│                                                                              │
│   PATH 1: Flink CDC (Database Changes)                                       │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐                              │
│   │ Datagen  │───►│PostgreSQL│───►│Flink CDC │──┐                           │
│   └────┬─────┘    └──────────┘    └──────────┘  │                           │
│        │                                         │  fact_events (CDC)        │
│        │   PATH 2: Kafka Connect (Streaming)     │  fact_conversions (CDC)   │
│        │   ┌──────────┐    ┌─────────────┐      │  dim_* tables (CDC)       │
│        └──►│  Kafka   │───►│Kafka Connect│──────┤                           │
│            └──────────┘    └─────────────┘      │  kafka_fact_events (Kafka)│
│                                                  │                           │
└──────────────────────────────────────────────────┼───────────────────────────┘
                                                   ▼
                                          ┌───────────────┐
                                          │ VeloDB Cloud  │
                                          └───────────────┘
```

**Key Design Decision**: The Kafka path writes to a **separate table** (`kafka_fact_events`) to avoid duplicating data from the CDC path. This lets you compare both paths side-by-side.

### Data Model: 5-Table Star Schema

```
                    ┌─────────────────┐
                    │   dim_users     │
                    │─────────────────│
                    │ user_id (PK)    │
                    │ email           │
                    │ name            │
                    │ signup_date     │
                    │ plan            │◄──── Free/Pro/Enterprise
                    │ country         │
                    │ industry        │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  dim_features   │  │  fact_events    │  │ fact_conversions│
│─────────────────│  │─────────────────│  │─────────────────│
│ feature_id (PK) │  │ event_id (PK)   │  │ conversion_id   │
│ feature_name    │◄─│ user_id (FK)    │  │ user_id (FK)    │
│ category        │  │ feature_id (FK) │  │ feature_id (FK) │
│ tier_required   │  │ campaign_id(FK) │  │ campaign_id(FK) │
└─────────────────┘  │ session_id      │  │ conversion_type │
                     │ event_type      │  │ conversion_time │
┌─────────────────┐  │ event_time      │  │ revenue         │
│  dim_campaigns  │  │ page_url        │  └─────────────────┘
│─────────────────│  └─────────────────┘
│ campaign_id(PK) │
│ campaign_name   │
│ channel         │◄──── Organic/Paid/Social/Email/Direct
│ source          │
│ medium          │
└─────────────────┘
```

### Data Flow Summary

| Source | Integration Method | Target Tables | Use Case |
|--------|-------------------|---------------|----------|
| PostgreSQL | Flink CDC | dim_users, dim_features, dim_campaigns, fact_events, fact_conversions | **Primary path**: Real-time CDC with full CRUD support |
| Kafka | Doris Kafka Connector | kafka_fact_events | **Streaming path**: High-throughput event ingestion |

> **Note**: Both paths run simultaneously. The datagen service writes to both PostgreSQL and Kafka, demonstrating dual-path ingestion without data duplication.

---

## 2. Prerequisites

### 2.1 VeloDB Cloud Account

1. Log in to [VeloDB Cloud Console](https://cloud.velodb.io)
2. Ensure you have an active cluster in **Running** state
3. Note down the following connection details:

| Parameter | Description | Example |
|-----------|-------------|---------|
| FE Host | Frontend node address | `cluster-xxx.velodb.io` |
| HTTP Port | Stream load port | `8030` |
| Query Port | MySQL protocol port | `9030` |
| Username | Database user | `admin` |
| Password | User password | `your_password` |

### 2.2 Local Environment

Verify the following are installed on your machine:

```bash
# Check Docker (version 20.x or higher required)
docker --version

# Check Docker Compose
docker-compose --version
# OR
docker compose version

# Check Java (required for Flink CDC)
java -version
# Expected: openjdk version "1.8.x" or "11.x" or higher
```

### 2.3 Network Requirements

- Outbound access to VeloDB Cloud (ports 8030, 9030)
- Local ports available: 5432 (PostgreSQL), 9092 (Kafka), 8083 (Kafka Connect), 8088 (Superset)

---

## 3. Environment Setup

### 3.1 Create Project Directory

```bash
mkdir -p velodb-lab && cd velodb-lab
```

### 3.2 Create Environment Configuration

Create a `.env` file with your settings:

```bash
cat > .env << 'EOF'
# ===========================================
# VeloDB Cloud Connection
# ===========================================
VELODB_FE_HOST=your-cluster.velodb.io
VELODB_HTTP_PORT=8030
VELODB_QUERY_PORT=9030
VELODB_USER=admin
VELODB_PASSWORD=your_password
VELODB_DATABASE=user_analytics

# ===========================================
# Local PostgreSQL
# ===========================================
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=labuser
POSTGRES_PASSWORD=labpass
POSTGRES_DB=user_analytics

# ===========================================
# Local Kafka
# ===========================================
KAFKA_BOOTSTRAP_SERVERS=kafka:29092

# ===========================================
# Superset
# ===========================================
SUPERSET_SECRET_KEY=velodb_lab_secret_key_2024
EOF
```

> **Important**: Replace `your-cluster.velodb.io` and `your_password` with your actual VeloDB Cloud credentials.

### 3.3 Docker Compose Services

The `docker-compose.yml` includes these services:

| Service | Port | Description |
|---------|------|-------------|
| **postgres** | 5432 | Source database with CDC enabled |
| **flink-cdc** | 8081 | Flink cluster syncing data to VeloDB |
| **datagen** | - | Continuous event generator |
| **superset** | 8088 | BI dashboard |

> **Note**: Kafka services are included but commented out. Uncomment them in `docker-compose.yml` to enable the alternative Kafka streaming path.

### 3.4 Start All Services

```bash
# Start all services (builds Flink image on first run)
docker-compose up -d --build

# Watch the startup logs
docker-compose logs -f

# Or check individual service status
docker-compose ps
```

Expected output after ~60 seconds:
```
NAME            STATUS              PORTS
postgres        running (healthy)   0.0.0.0:5432->5432/tcp
flink-cdc       running             0.0.0.0:8081->8081/tcp
datagen         running
superset        running             0.0.0.0:8088->8088/tcp
```

### 3.5 Verify Services

```bash
# Check PostgreSQL has seed data
docker exec postgres psql -U labuser -d user_analytics -c "SELECT COUNT(*) FROM dim_users;"

# Check Flink CDC is running
docker logs flink-cdc | tail -20

# Access Flink Web UI
open http://localhost:8081

# Access Superset
open http://localhost:8088
```

### 3.6 Create VeloDB Target Database

Connect to VeloDB SQL Editor in the cloud console and run:

```sql
-- Create the lab database
CREATE DATABASE IF NOT EXISTS user_analytics;

-- Verify
SHOW DATABASES LIKE 'user_analytics';
```

### 3.6 Verify Connectivity

Test connection to VeloDB from your local machine:

```bash
# Using MySQL client
mysql -h $VELODB_FE_HOST -P 9030 -u $VELODB_USER -p$VELODB_PASSWORD -e "SHOW DATABASES;"

# Or using curl to test HTTP port
curl -v telnet://$VELODB_FE_HOST:8030
```

---

## 4. Module 1: PostgreSQL CDC with Flink

This module demonstrates real-time change data capture from PostgreSQL to VeloDB for **dimension tables**.

### 4.1 Create Source Tables in PostgreSQL

Connect to PostgreSQL:

```bash
docker exec -it postgres psql -U labuser -d user_analytics
```

Create the dimension tables:

```sql
-- Users dimension table
CREATE TABLE dim_users (
    user_id SERIAL PRIMARY KEY,
    email VARCHAR(200) NOT NULL UNIQUE,
    name VARCHAR(100),
    signup_date DATE DEFAULT CURRENT_DATE,
    plan VARCHAR(20) DEFAULT 'Free',        -- Free, Pro, Enterprise
    country VARCHAR(50),
    industry VARCHAR(50),
    properties JSONB
);

-- Features dimension table
CREATE TABLE dim_features (
    feature_id SERIAL PRIMARY KEY,
    feature_name VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    description TEXT,
    tier_required VARCHAR(20) DEFAULT 'Free'
);

-- Campaigns dimension table
CREATE TABLE dim_campaigns (
    campaign_id SERIAL PRIMARY KEY,
    campaign_name VARCHAR(100),
    channel VARCHAR(50),                     -- Organic, Paid, Social, Email, Direct
    source VARCHAR(50),
    medium VARCHAR(50)
);

-- Enable REPLICA IDENTITY FULL for CDC to capture DELETE operations
ALTER TABLE dim_users REPLICA IDENTITY FULL;
ALTER TABLE dim_features REPLICA IDENTITY FULL;
ALTER TABLE dim_campaigns REPLICA IDENTITY FULL;

-- Verify tables created
\dt
```

Exit psql: `\q`

### 4.2 Create Target Tables in VeloDB

In VeloDB SQL Editor, run the complete schema for all 5 tables:

```sql
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

-- Create indexes for fast filtering
CREATE INDEX idx_event_type ON fact_events(event_type) USING INVERTED;
CREATE INDEX idx_event_time ON fact_events(event_time) USING INVERTED;
CREATE INDEX idx_conversion_type ON fact_conversions(conversion_type) USING INVERTED;

-- Verify all tables
SHOW TABLES;
```

### 4.3 Flink CDC (Included in Docker Compose)

**Flink CDC is included in Docker Compose and starts automatically!**

The `flink-cdc` service:
- Waits for PostgreSQL to be ready with seed data
- Connects to your VeloDB Cloud instance
- Syncs all 5 tables in real-time

**Check Flink CDC status:**
```bash
# View Flink logs
docker logs -f flink-cdc

# Access Flink Web UI
open http://localhost:8081
```

### 4.4 How the CDC Sync Works

The Flink CDC job syncs these tables from PostgreSQL to VeloDB:

| Source Table | Target Table | Sync Mode |
|--------------|--------------|-----------|
| `public.dim_users` | `user_analytics.dim_users` | CDC (upsert/delete) |
| `public.dim_features` | `user_analytics.dim_features` | CDC (upsert/delete) |
| `public.dim_campaigns` | `user_analytics.dim_campaigns` | CDC (upsert/delete) |
| `public.fact_events` | `user_analytics.fact_events` | CDC (append) |
| `public.fact_conversions` | `user_analytics.fact_conversions` | CDC (append) |

The CDC job captures:
- **INSERT** - New rows immediately synced
- **UPDATE** - Changes captured and applied
- **DELETE** - Rows removed from VeloDB

### 4.5 Seed Data (Auto-Loaded)

Seed data is automatically loaded when PostgreSQL starts via `init_postgres.sql`:

**dim_users** (10 users across Free/Pro/Enterprise plans):
```
Alex Chen (Enterprise), Sam Smith (Pro), Jordan Garcia (Free)...
```

**dim_features** (10 product features):
```
Analytics Builder, Analytics Manager, Dashboard Viewer, Export Manager...
```

**dim_campaigns** (5 marketing channels):
```
Organic Search, Paid Search, Social Media, Email Newsletter, Direct Traffic
```

To view the seed data:
INSERT INTO dim_campaigns (campaign_name, channel, source, medium) VALUES
    ('Organic Search', 'Organic', 'google', 'organic'),
    ('Paid Search', 'Paid', 'google', 'cpc'),
    ('Social Media', 'Social', 'linkedin', 'social'),
    ('Email Newsletter', 'Email', 'newsletter', 'email'),
    ('Direct Traffic', 'Direct', 'direct', 'none');

-- Verify data
SELECT * FROM dim_users;
SELECT * FROM dim_features;
SELECT * FROM dim_campaigns;
```

### 4.6 Verify Data Sync in VeloDB

Wait 5-10 seconds, then check VeloDB:

```sql
USE user_analytics;

-- Check users synced
SELECT * FROM dim_users ORDER BY user_id;

-- Check features synced
SELECT * FROM dim_features ORDER BY feature_id;

-- Check campaigns synced
SELECT * FROM dim_campaigns ORDER BY campaign_id;

-- Verify counts match
SELECT 'dim_users' as tbl, COUNT(*) as cnt FROM dim_users
UNION ALL SELECT 'dim_features', COUNT(*) FROM dim_features
UNION ALL SELECT 'dim_campaigns', COUNT(*) FROM dim_campaigns;
```

### 4.7 Test Real-Time CDC

**Test INSERT** - In PostgreSQL:
```sql
INSERT INTO dim_users (email, name, plan, country, industry)
VALUES ('new.user@example.com', 'New User', 'Pro', 'USA', 'Technology');
```

Check VeloDB within seconds:
```sql
SELECT * FROM dim_users WHERE email = 'new.user@example.com';
```

**Test UPDATE** - In PostgreSQL:
```sql
UPDATE dim_users SET plan = 'Enterprise' WHERE user_id = 1;
```

Check VeloDB:
```sql
SELECT user_id, name, plan FROM dim_users WHERE user_id = 1;
```

**Test DELETE** - In PostgreSQL:
```sql
DELETE FROM dim_campaigns WHERE campaign_id = 5;
```

Check VeloDB:
```sql
SELECT * FROM dim_campaigns WHERE campaign_id = 5;
-- Should return empty result
```

---

## 5. Module 2: Kafka Integration

This module demonstrates streaming events from Kafka to VeloDB using the Doris Kafka Connector. The datagen service automatically sends events to both PostgreSQL and Kafka, allowing you to see both paths working in parallel.

### 5.1 Kafka Services (Auto-Started)

When you run `docker compose up`, these Kafka services start automatically:
- **Zookeeper** - Kafka coordination
- **Kafka** - Message broker (port 9092)
- **Kafka Connect** - Doris sink connector (port 8083)

Topics are auto-created by Kafka when datagen starts producing messages.

### 5.2 Create Kafka Target Table in VeloDB

The Kafka path writes to a **separate table** to avoid duplicating CDC data:

```sql
USE user_analytics;

-- Kafka events table (separate from Flink CDC to avoid duplicates)
-- IMPORTANT: merge-on-write must be DISABLED for Kafka Connect 2PC compatibility
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
    "enable_unique_key_merge_on_write" = "false"  -- Required for Kafka Connect!
);

-- Verify table created
SHOW CREATE TABLE kafka_fact_events;
```

> **⚠️ Critical**: The `enable_unique_key_merge_on_write` must be `false` for Kafka Connect. The Doris Kafka Connector uses 2-phase commit which is incompatible with merge-on-write tables.

### 5.3 Kafka Connect (Pre-Configured)

The Doris Kafka Connector is pre-installed in the `kafka-connect` Docker image. It auto-registers on startup using environment variables from your `.env` file.

**Verify Kafka Connect is ready:**
```bash
curl -s http://localhost:8083/ | python3 -m json.tool
```

**Check if connector is registered:**
```bash
curl -s http://localhost:8083/connectors
# Expected: ["velodb-kafka-events-sink"]
```

### 5.4 Manual Connector Registration (If Needed)

If the connector didn't auto-register, deploy it manually:

```bash
# Replace placeholders with your VeloDB credentials
curl -X POST http://localhost:8083/connectors \
    -H "Content-Type: application/json" \
    -d '{
    "name": "velodb-kafka-events-sink",
    "config": {
        "connector.class": "org.apache.doris.kafka.connector.DorisSinkConnector",
        "tasks.max": "1",
        "topics": "fact_events",
        "doris.urls": "YOUR_VELODB_HOST",
        "doris.http.port": "8080",
        "doris.query.port": "9030",
        "doris.user": "YOUR_USER",
        "doris.password": "YOUR_PASSWORD",
        "doris.database": "user_analytics",
        "doris.topic2table.map": "fact_events:kafka_fact_events",
        "key.converter": "org.apache.kafka.connect.storage.StringConverter",
        "value.converter": "org.apache.kafka.connect.json.JsonConverter",
        "value.converter.schemas.enable": "false",
        "buffer.count.records": "1000",
        "buffer.flush.time": "10",
        "buffer.size.bytes": "1000000",
        "doris.request.connect.timeout.ms": "30000",
        "doris.request.read.timeout.ms": "30000"
    }
}'
```

> **Important Configuration Notes:**
> - Use `doris.topic2table.map` instead of `doris.table` to map topics to tables
> - Format: `"topic_name:table_name"` (e.g., `"fact_events:kafka_fact_events"`)
> - `buffer.flush.time`: Lower values (10s) give faster feedback during demos
> - `doris.http.port`: Usually `8080` for VeloDB Cloud

**Verify Connector Status:**

```bash
# Check connector status
curl -s http://localhost:8083/connectors/velodb-kafka-events-sink/status | python3 -m json.tool
```

Expected output:
```json
{
    "name": "velodb-kafka-events-sink",
    "connector": { "state": "RUNNING" },
    "tasks": [{ "id": 0, "state": "RUNNING" }]
}
```

### 5.5 Produce Test Messages

**Send Event:**

```bash
echo '{"event_id":1,"user_id":1,"feature_id":1,"campaign_id":1,"session_id":"sess_12345","event_type":"page_view","event_time":"2024-01-15 10:30:00","page_url":"/app/dashboard","search_query":null,"properties":"{\"duration\":120}"}' | \
docker exec -i kafka kafka-console-producer \
    --bootstrap-server localhost:9092 \
    --topic fact_events
```

**Send Conversion:**

```bash
echo '{"conversion_id":1,"user_id":1,"feature_id":2,"campaign_id":1,"conversion_type":"upgrade","conversion_time":"2024-01-15 10:35:00","plan_from":"Free","plan_to":"Pro","revenue":99.00,"properties":"{\"source\":\"app\"}"}' | \
docker exec -i kafka kafka-console-producer \
    --bootstrap-server localhost:9092 \
    --topic fact_conversions
```

### 5.6 Start Continuous Data Generation

The datagen service is already configured in docker-compose. Start it:

```bash
# The datagen container generates events and conversions continuously
docker-compose up -d datagen

# Check logs
docker logs -f datagen
```

Or run manually:

```python
#!/usr/bin/env python3
import json
import time
import random
from datetime import datetime
from kafka import KafkaProducer

producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

EVENT_TYPES = ['page_view', 'feature_use', 'search', 'click', 'scroll', 'form_start', 'form_submit', 'error']
PAGES = ['/app/dashboard', '/app/analytics', '/app/settings', '/app/reports', '/app/integrations']
CONVERSION_TYPES = ['signup', 'upgrade', 'purchase', 'churn']
PLANS = ['Free', 'Pro', 'Enterprise']

event_id = 0
conversion_id = 0

def generate_event():
    global event_id
    event_id += 1
    return {
        'event_id': event_id,
        'user_id': random.randint(1, 10),
        'feature_id': random.randint(1, 10),
        'campaign_id': random.randint(1, 5),
        'session_id': f"sess_{random.randint(1, 100000)}",
        'event_type': random.choice(EVENT_TYPES),
        'event_time': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
        'page_url': random.choice(PAGES),
        'search_query': None,
        'properties': json.dumps({'duration': random.randint(1, 300)})
    }

def generate_conversion():
    global conversion_id
    conversion_id += 1
    conv_type = random.choice(CONVERSION_TYPES)
    return {
        'conversion_id': conversion_id,
        'user_id': random.randint(1, 10),
        'feature_id': random.randint(1, 10),
        'campaign_id': random.randint(1, 5),
        'conversion_type': conv_type,
        'conversion_time': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
        'plan_from': random.choice([None, 'Free', 'Pro']),
        'plan_to': random.choice(['Pro', 'Enterprise']) if conv_type != 'churn' else None,
        'revenue': round(random.uniform(10, 500), 2),
        'properties': json.dumps({'source': 'app'})
    }

print("Generating events and conversions... Press Ctrl+C to stop")
count = 0
while True:
    # Send 10 events per conversion
    for _ in range(10):
        producer.send('fact_events', generate_event())
    producer.send('fact_conversions', generate_conversion())
    count += 1
    if count % 10 == 0:
        print(f"Sent {count*10} events, {count} conversions")
    time.sleep(0.2)  # 5 events per second
```

Run the generator:
```bash
pip install kafka-python
python kafka_datagen.py
```

### 5.7 Verify Data in VeloDB

```sql
USE user_analytics;

-- Check all table counts
SELECT 'dim_users' as tbl, COUNT(*) as cnt FROM dim_users
UNION ALL SELECT 'dim_features', COUNT(*) FROM dim_features
UNION ALL SELECT 'dim_campaigns', COUNT(*) FROM dim_campaigns
UNION ALL SELECT 'fact_events', COUNT(*) FROM fact_events
UNION ALL SELECT 'fact_conversions', COUNT(*) FROM fact_conversions;

-- Events by type
SELECT event_type, COUNT(*) as count
FROM fact_events
GROUP BY event_type
ORDER BY count DESC;

-- Recent events with user and feature info
SELECT
    e.event_id,
    u.name as user_name,
    u.plan,
    f.feature_name,
    e.event_type,
    e.event_time
FROM fact_events e
JOIN dim_users u ON e.user_id = u.user_id
JOIN dim_features f ON e.feature_id = f.feature_id
ORDER BY e.event_time DESC
LIMIT 10;

-- Conversions with revenue
SELECT
    c.conversion_type,
    COUNT(*) as count,
    SUM(c.revenue) as total_revenue
FROM fact_conversions c
GROUP BY c.conversion_type
ORDER BY total_revenue DESC;
```

---

## 6. Module 3: Superset BI Dashboard

This module creates the **VeloDB User Analytics** dashboard matching the reference design.

![Dashboard Preview](./docs/user-analytics-1.png)

### 6.1 Access Superset

Open in browser: **http://localhost:8088**

Login credentials:
- **Username**: `admin`
- **Password**: `admin`

### 6.2 Add VeloDB Database Connection

1. Click **Settings** (gear icon) → **Database Connections**
2. Click **+ Database**
3. Select **MySQL** as database type
4. Enter SQLAlchemy URI:

```
mysql+pymysql://YOUR_USER:YOUR_PASSWORD@YOUR_VELODB_HOST:9030/user_analytics
```

Example:
```
mysql+pymysql://admin:mypassword@cluster-abc.velodb.io:9030/user_analytics
```

5. Click **Test Connection**
6. Click **Connect**

### 6.3 Create Datasets

Navigate to **Data** → **Datasets** → **+ Dataset**

Create datasets for the star schema tables:

| Database | Schema | Table | Description |
|----------|--------|-------|-------------|
| VeloDB | user_analytics | dim_users | User dimension |
| VeloDB | user_analytics | dim_features | Feature dimension |
| VeloDB | user_analytics | dim_campaigns | Campaign dimension |
| VeloDB | user_analytics | fact_events | Event facts |
| VeloDB | user_analytics | fact_conversions | Conversion facts |

### 6.4 Create Charts

The dashboard includes these visualizations:

#### Chart 1: KPI Cards (Active Users, Events, Sessions, Conversions, Revenue)

Create a SQL dataset for KPIs:

```sql
SELECT
    (SELECT COUNT(DISTINCT user_id) FROM fact_events WHERE event_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)) AS active_users,
    (SELECT COUNT(*) FROM fact_events WHERE event_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)) AS total_events,
    (SELECT COUNT(DISTINCT session_id) FROM fact_events WHERE event_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)) AS total_sessions,
    (SELECT COUNT(*) FROM fact_conversions WHERE conversion_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)) AS total_conversions,
    (SELECT ROUND(SUM(revenue), 0) FROM fact_conversions WHERE conversion_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)) AS total_revenue
```

Create 5 **Big Number** charts, one for each metric.

#### Chart 2: Hourly Activity (24h)

1. **Charts** → **+ Chart**
2. Chart type: **Time-series Line Chart**
3. SQL:
```sql
SELECT
    DATE_FORMAT(event_time, '%Y-%m-%d %H:00:00') AS hour,
    COUNT(*) AS events,
    COUNT(DISTINCT user_id) AS users
FROM fact_events
WHERE event_time >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
GROUP BY DATE_FORMAT(event_time, '%Y-%m-%d %H:00:00')
ORDER BY hour
```
4. X-Axis: `hour`
5. Metrics: `events`, `users`

#### Chart 3: Daily Activity (30d)

Chart type: **Area Chart**
```sql
SELECT
    DATE(e.event_time) AS activity_date,
    COUNT(DISTINCT e.user_id) AS users,
    COUNT(*) AS events,
    COUNT(DISTINCT e.session_id) AS sessions
FROM fact_events e
WHERE e.event_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY DATE(e.event_time)
ORDER BY activity_date
```

#### Chart 4: Activity by Plan

Chart type: **Stacked Area Chart**
```sql
SELECT
    DATE(e.event_time) AS activity_date,
    u.plan,
    COUNT(DISTINCT e.user_id) AS users
FROM fact_events e
JOIN dim_users u ON e.user_id = u.user_id
WHERE e.event_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY DATE(e.event_time), u.plan
ORDER BY activity_date
```
- Group by: `plan`
- Stack: enabled

#### Chart 5: Top 10 Features

Chart type: **Horizontal Bar Chart**
```sql
SELECT
    f.feature_name,
    COUNT(*) AS total_uses
FROM fact_events e
JOIN dim_features f ON e.feature_id = f.feature_id
WHERE e.event_type = 'feature_use'
  AND e.event_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY f.feature_name
ORDER BY total_uses DESC
LIMIT 10
```

#### Chart 6: Feature Adoption Heatmap

Chart type: **Heatmap**
```sql
SELECT
    f.feature_name,
    u.plan,
    COUNT(*) as usage_count
FROM fact_events e
JOIN dim_users u ON e.user_id = u.user_id
JOIN dim_features f ON e.feature_id = f.feature_id
WHERE e.event_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY f.feature_name, u.plan
```
- X-axis: `plan`
- Y-axis: `feature_name`
- Metric: `usage_count`
- Color scheme: Oranges

### 6.5 Build Dashboard

1. **Dashboards** → **+ Dashboard**
2. Name: **VeloDB User Analytics**
3. Click **Edit Dashboard**
4. Drag charts from the right panel into the layout:

```
┌─────────────────────────────────────────────────────────────────┐
│                   VeloDB User Analytics                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │  Active  │  │  Total   │  │ Sessions │  │ Revenue  │        │
│  │  Users   │  │  Events  │  │          │  │          │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Hourly Activity (Line Chart)                 │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────┐  ┌─────────────────────────────┐   │
│  │   Events by Plan        │  │    Top 10 Features          │   │
│  │      (Pie Chart)        │  │    (Bar Chart)              │   │
│  └─────────────────────────┘  └─────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │           Feature Adoption Heatmap                        │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

5. Click **Save**

### 6.6 Enable Auto-Refresh

1. In dashboard view, click the **refresh icon**
2. Select interval: **10 seconds**
3. Dashboard will auto-update with new data

---

## 7. Module 4: End-to-End Verification

### 7.1 Verification Checklist

Run through this checklist to verify your lab setup:

```bash
# 1. Check Docker services
docker compose ps

# 2. Check PostgreSQL
docker exec postgres psql -U labuser -d user_analytics -c "SELECT COUNT(*) FROM fact_events;"

# 3. Check Flink CDC jobs
curl -s http://localhost:8081/jobs/overview | python3 -c "
import sys, json
for job in json.load(sys.stdin)['jobs']:
    print(f\"{job['state']:10} {job['name'].split('.')[-1]}\")"

# 4. Check Superset
curl -s http://localhost:8088/health
```

### 7.2 Verify Data Counts (Both Paths)

In VeloDB SQL Editor:

```sql
USE user_analytics;

-- Check all tables including Kafka path
SELECT 'PATH 1: Flink CDC' as source, '' as table_name, '' as rows
UNION ALL SELECT '', 'dim_users', CAST(COUNT(*) AS CHAR) FROM dim_users
UNION ALL SELECT '', 'dim_features', CAST(COUNT(*) AS CHAR) FROM dim_features
UNION ALL SELECT '', 'dim_campaigns', CAST(COUNT(*) AS CHAR) FROM dim_campaigns
UNION ALL SELECT '', 'fact_events', CAST(COUNT(*) AS CHAR) FROM fact_events
UNION ALL SELECT '', 'fact_conversions', CAST(COUNT(*) AS CHAR) FROM fact_conversions
UNION ALL SELECT 'PATH 2: Kafka Connect', '', ''
UNION ALL SELECT '', 'kafka_fact_events', CAST(COUNT(*) AS CHAR) FROM kafka_fact_events;
```

**Expected Results:**
- CDC tables should have growing counts (dim_users ~10+, fact_events ~1000s)
- kafka_fact_events should also be growing (synced from Kafka)

### 7.3 Verify Real-Time Sync

**PostgreSQL CDC Test:**

1. Insert in PostgreSQL:
```bash
docker exec postgres psql -U labuser -d user_analytics -c "
INSERT INTO dim_users (email, name, plan, country, industry)
VALUES ('test.verify@example.com', 'Test User', 'Pro', 'USA', 'Testing');"
```

2. Check VeloDB (within 10-15 seconds):
```sql
SELECT * FROM user_analytics.dim_users WHERE email = 'test.verify@example.com';
```

**Verify Stream Load Success:**

```bash
docker logs flink-cdc 2>&1 | grep "Status.*Success" | tail -3
```

### 7.4 Verify Superset Dashboard

1. Open http://localhost:8088
2. Navigate to your dashboard
3. Confirm all charts display data
4. Enable auto-refresh and verify updates

---

## 8. Troubleshooting

### PostgreSQL CDC Issues

**Replication slot already exists:**
```sql
-- In PostgreSQL
SELECT pg_drop_replication_slot('flink_cdc_slot');
```

**WAL level not set:**
```bash
docker exec -it postgres psql -U labuser -c "SHOW wal_level;"
# Should show 'logical'
```

### Kafka Connect Issues

**Connector in FAILED state:**
```bash
# Check error details
curl -s http://localhost:8083/connectors/velodb-kafka-events-sink/status | python3 -c "
import sys, json
data = json.load(sys.stdin)
if data.get('tasks'):
    print(data['tasks'][0].get('trace', 'No trace')[:500])"
```

**Common Error: "stream load 2pc is unsupported for mow table"**

This error occurs when the target table has `enable_unique_key_merge_on_write = true`. Fix:
```sql
-- Recreate table without merge-on-write
DROP TABLE IF EXISTS kafka_fact_events;
CREATE TABLE kafka_fact_events (
    -- ... columns ...
) UNIQUE KEY(event_id)
DISTRIBUTED BY HASH(event_id) BUCKETS 4
PROPERTIES (
    "replication_num" = "1",
    "enable_unique_key_merge_on_write" = "false"  -- Must be false!
);
```

**Common Error: "table not found, tableName=null"**

This error means the connector config is using `doris.table` instead of `doris.topic2table.map`. Fix:
```json
{
    "doris.topic2table.map": "fact_events:kafka_fact_events"
}
```

**Restart connector task:**
```bash
curl -X POST http://localhost:8083/connectors/velodb-kafka-events-sink/tasks/0/restart
```

**Delete and recreate connector:**
```bash
curl -X DELETE http://localhost:8083/connectors/velodb-kafka-events-sink
# Then redeploy with correct config
```

### VeloDB Connection Issues

**Test connectivity:**
```bash
# Test MySQL protocol (port 9030)
mysql -h YOUR_HOST -P 9030 -u YOUR_USER -p -e "SELECT 1;"

# Test HTTP port (port 8030 or 8080)
curl -v http://YOUR_HOST:8080/api/bootstrap
```

**Common Error: "Access denied for user 'admin@x.x.x.x'"**

This error usually means:
1. **IP Whitelist**: Your IP is not whitelisted in VeloDB Cloud
   - Go to VeloDB Cloud Console → Cluster Settings → Network
   - Check your public IP: `curl -s ifconfig.me`
   - Ensure your IP (or `0.0.0.0/0` for "Anywhere") is in the whitelist

2. **Incorrect Password**: Verify your credentials are correct
   - Check for special characters that may need escaping
   - Try connecting via VeloDB Cloud SQL Editor first

3. **Wrong Port**: Ensure you're using the correct port
   - Query port: Usually `9030` (MySQL protocol)
   - HTTP port: Usually `8030` or `8080` (Stream Load)

**Verify VeloDB credentials work:**
```bash
# From your local machine, find your public IP
curl -s ifconfig.me

# Test the HTTP API first (doesn't require IP whitelist for some endpoints)
curl -s "http://YOUR_HOST:8080/api/bootstrap"

# If HTTP works but MySQL doesn't, it's likely an IP whitelist issue
```

**For Docker containers (Flink CDC):**
The Flink container connects from a Docker network, which exits through your host machine's public IP. Make sure your IP is whitelisted.

**Check IP whitelist:**
- Go to VeloDB Cloud Console → Cluster Settings → Network
- Add your public IP: `curl -s ifconfig.me`
- Or temporarily set to "Anywhere" (0.0.0.0/0) for testing

### Superset Issues

**Cannot connect to VeloDB:**
- Verify connection string format
- Test with: `mysql+pymysql://user:pass@host:9030/database`
- Ensure pymysql is installed in Superset container

**Charts not loading:**
- Check browser console for errors
- Verify dataset query works in SQL Lab

---

## 9. Cleanup

### Stop Services

```bash
# Stop all containers
docker-compose down

# Remove volumes (deletes all data)
docker-compose down -v
```

### Clean Up Flink CDC

```bash
# Stop Flink job (if running in foreground, Ctrl+C)
# Or cancel via Flink Web UI at http://localhost:8081
```

### Clean Up VeloDB (Optional)

```sql
-- Drop lab database
DROP DATABASE user_analytics;
```

---

## 10. Appendix: Configuration Files

### A. Complete Docker Compose

See Section 3.3 above.

### B. VeloDB Schema SQL

The complete schema is in `flink/velodb_schema.sql`. Here's a summary:

```sql
-- Complete schema for user_analytics database
-- Run in VeloDB SQL Editor

CREATE DATABASE IF NOT EXISTS user_analytics;
USE user_analytics;

-- Dimension Tables (UNIQUE KEY for upserts)
CREATE TABLE IF NOT EXISTS dim_users (
    user_id BIGINT,
    email VARCHAR(200),
    name VARCHAR(100),
    signup_date DATE,
    plan VARCHAR(20),
    country VARCHAR(50),
    industry VARCHAR(50),
    properties VARCHAR(65533)
) UNIQUE KEY(user_id)
DISTRIBUTED BY HASH(user_id) BUCKETS 4
PROPERTIES ("replication_num" = "1", "enable_unique_key_merge_on_write" = "true");

CREATE TABLE IF NOT EXISTS dim_features (
    feature_id BIGINT,
    feature_name VARCHAR(100),
    category VARCHAR(50),
    description TEXT,
    tier_required VARCHAR(20)
) UNIQUE KEY(feature_id)
DISTRIBUTED BY HASH(feature_id) BUCKETS 4
PROPERTIES ("replication_num" = "1", "enable_unique_key_merge_on_write" = "true");

CREATE TABLE IF NOT EXISTS dim_campaigns (
    campaign_id BIGINT,
    campaign_name VARCHAR(100),
    channel VARCHAR(50),
    source VARCHAR(50),
    medium VARCHAR(50)
) UNIQUE KEY(campaign_id)
DISTRIBUTED BY HASH(campaign_id) BUCKETS 4
PROPERTIES ("replication_num" = "1", "enable_unique_key_merge_on_write" = "true");

-- Fact Tables
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
) UNIQUE KEY(event_id)
DISTRIBUTED BY HASH(user_id) BUCKETS 4
PROPERTIES ("replication_num" = "1", "enable_unique_key_merge_on_write" = "true");

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
) UNIQUE KEY(conversion_id)
DISTRIBUTED BY HASH(user_id) BUCKETS 4
PROPERTIES ("replication_num" = "1", "enable_unique_key_merge_on_write" = "true");
```

### C. Kafka Connector Configuration

**User Events Sink:**
```json
{
    "name": "velodb-user-events-sink",
    "config": {
        "connector.class": "org.apache.doris.kafka.connector.DorisSinkConnector",
        "tasks.max": "1",
        "topics": "user_events",
        "doris.urls": "YOUR_VELODB_HOST",
        "doris.http.port": "8030",
        "doris.query.port": "9030",
        "doris.user": "YOUR_USER",
        "doris.password": "YOUR_PASSWORD",
        "doris.database": "user_analytics",
        "doris.table": "user_events",
        "key.converter": "org.apache.kafka.connect.storage.StringConverter",
        "value.converter": "org.apache.kafka.connect.json.JsonConverter",
        "value.converter.schemas.enable": "false",
        "buffer.count.records": "10000",
        "buffer.flush.time": "60"
    }
}
```

---

## Summary

In this lab, you learned how to:

1. **Set up PostgreSQL CDC** using Flink CDC to capture real-time database changes
2. **Configure Kafka streaming** using Doris Kafka Connector to ingest event data
3. **Build BI dashboards** with Apache Superset for real-time analytics
4. **Verify end-to-end** data flow from sources to visualization

### Architecture Implemented

```
PostgreSQL ──► Flink CDC ──► VeloDB Cloud ◄── Kafka Connect ◄── Kafka
                                  │
                                  ▼
                              Superset
                            (Dashboard)
```

### Key Takeaways

- VeloDB supports multiple real-time ingestion patterns
- Flink CDC enables seamless PostgreSQL → VeloDB sync with INSERT/UPDATE/DELETE support
- Kafka Connect provides scalable streaming ingestion
- Superset integrates natively via MySQL protocol

---

**Congratulations on completing the VeloDB Real-Time Data Integration Lab!**

For questions or support, contact your VeloDB solutions architect or visit [docs.velodb.io](https://docs.velodb.io).
