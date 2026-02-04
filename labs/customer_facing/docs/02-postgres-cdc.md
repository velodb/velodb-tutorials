# Module 2: PostgreSQL CDC with Flink

This module explains how Change Data Capture (CDC) works to sync data from PostgreSQL to VeloDB in real-time.

## Architecture

```
PostgreSQL (user_analytics)  →  Flink CDC  →  VeloDB Cloud (user_analytics)
     ↓                            ↓                    ↓
 [dim_users]                 WAL Decoding         [dim_users]
 [dim_features]              Streaming            [dim_features]
 [dim_campaigns]             Transform            [dim_campaigns]
 [fact_events]                                    [fact_events]
 [fact_conversions]                               [fact_conversions]
```

## Data Model: 5-Table Star Schema

### Dimension Tables

| Table | Primary Key | Description |
|-------|-------------|-------------|
| `dim_users` | user_id | User profiles with plan, country, industry |
| `dim_features` | feature_id | Product features by tier (Free/Pro/Enterprise) |
| `dim_campaigns` | campaign_id | Marketing campaigns and channels |

### Fact Tables

| Table | Primary Key | Description |
|-------|-------------|-------------|
| `fact_events` | event_id | User behavior events (~5 per second) |
| `fact_conversions` | conversion_id | Revenue and conversion events |

## How CDC Works in This Lab

### Automatic Setup via Docker

When you run `docker compose up -d`, the Flink CDC pipeline starts automatically:

1. **PostgreSQL** initializes with seed data (via `datagen/init_postgres.sql`)
2. **Flink CDC** container starts and connects to PostgreSQL
3. **CDC jobs** are submitted (one per table)
4. **Datagen** continuously generates new events

### PostgreSQL Configuration

PostgreSQL is pre-configured for logical replication:

```yaml
# docker-compose.yml
command:
  - "postgres"
  - "-c"
  - "wal_level=logical"
  - "-c"
  - "max_replication_slots=10"
  - "-c"
  - "max_wal_senders=10"
```

Tables have `REPLICA IDENTITY FULL` for complete CDC:

```sql
-- From datagen/init_postgres.sql
ALTER TABLE dim_users REPLICA IDENTITY FULL;
ALTER TABLE fact_events REPLICA IDENTITY FULL;
-- etc.
```

### Flink CDC Job Configuration

The CDC job is defined in `flink/cdc-job.sql`:

```sql
-- Source table (PostgreSQL)
CREATE TABLE pg_dim_users (
    user_id INT,
    email STRING,
    name STRING,
    ...
    PRIMARY KEY (user_id) NOT ENFORCED
) WITH (
    'connector' = 'postgres-cdc',
    'hostname' = '${POSTGRES_HOST}',
    'port' = '${POSTGRES_PORT}',
    'database-name' = '${POSTGRES_DB}',
    'table-name' = 'dim_users',
    'slot.name' = 'flink_dim_users_slot',
    'decoding.plugin.name' = 'pgoutput'
);

-- Sink table (VeloDB)
CREATE TABLE velodb_dim_users (
    ...
) WITH (
    'connector' = 'doris',
    'fenodes' = '${VELODB_FE_HOST}:${VELODB_HTTP_PORT}',
    'table.identifier' = '${VELODB_DATABASE}.dim_users',
    'username' = '${VELODB_USER}',
    'password' = '${VELODB_PASSWORD}'
);

-- Sync pipeline
INSERT INTO velodb_dim_users SELECT * FROM pg_dim_users;
```

## Monitoring CDC Jobs

### Flink Web UI

Access http://localhost:8081 to:

- View all 5 running jobs
- Monitor throughput and latency
- Check checkpoint status
- View task manager resources

### Command Line

```bash
# Check job status
curl -s http://localhost:8081/jobs/overview | python3 -c "
import sys, json
for job in json.load(sys.stdin)['jobs']:
    name = job['name'].split('.')[-1]
    print(f\"{job['state']:10} {name}\")"

# Expected output:
# RUNNING    velodb_dim_users
# RUNNING    velodb_dim_features
# RUNNING    velodb_dim_campaigns
# RUNNING    velodb_fact_events
# RUNNING    velodb_fact_conversions
```

### Check Stream Load Status

```bash
# Look for successful stream loads
docker logs flink-cdc 2>&1 | grep "Status.*Success" | tail -5

# Check load results
docker logs flink-cdc 2>&1 | grep -A5 "load Result" | tail -20
```

## Verifying Data Sync

### Compare Source and Target

```bash
# PostgreSQL (source)
docker exec postgres psql -U labuser -d user_analytics -c "
SELECT 'dim_users' as tbl, COUNT(*) FROM dim_users
UNION ALL SELECT 'dim_features', COUNT(*) FROM dim_features
UNION ALL SELECT 'dim_campaigns', COUNT(*) FROM dim_campaigns
UNION ALL SELECT 'fact_events', COUNT(*) FROM fact_events
UNION ALL SELECT 'fact_conversions', COUNT(*) FROM fact_conversions;"

# VeloDB (target)
mysql -h $VELODB_FE_HOST -P 9030 -u $VELODB_USER -p$VELODB_PASSWORD -e "
USE user_analytics;
SELECT 'dim_users' as tbl, COUNT(*) FROM dim_users
UNION ALL SELECT 'dim_features', COUNT(*) FROM dim_features
UNION ALL SELECT 'dim_campaigns', COUNT(*) FROM dim_campaigns
UNION ALL SELECT 'fact_events', COUNT(*) FROM fact_events
UNION ALL SELECT 'fact_conversions', COUNT(*) FROM fact_conversions;"
```

### Watch Real-Time Sync

Open two terminals:

```bash
# Terminal 1: Watch PostgreSQL
watch -n 5 'docker exec postgres psql -U labuser -d user_analytics -c "SELECT COUNT(*) as events FROM fact_events;"'

# Terminal 2: Watch VeloDB
watch -n 5 'mysql -h YOUR_HOST -P 9030 -u admin -pPASSWORD -e "SELECT COUNT(*) FROM user_analytics.fact_events;"'
```

## Test CDC Operations

### Test INSERT

```bash
# Insert a new user in PostgreSQL
docker exec postgres psql -U labuser -d user_analytics -c "
INSERT INTO dim_users (email, name, plan, country, industry)
VALUES ('test.user@example.com', 'Test User', 'Pro', 'USA', 'Technology');"

# Check in VeloDB (within seconds)
mysql -h $VELODB_FE_HOST -P 9030 -u $VELODB_USER -p$VELODB_PASSWORD -e "
SELECT * FROM user_analytics.dim_users WHERE email = 'test.user@example.com';"
```

### Test UPDATE

```bash
# Update user plan
docker exec postgres psql -U labuser -d user_analytics -c "
UPDATE dim_users SET plan = 'Enterprise' WHERE email = 'test.user@example.com';"

# Verify in VeloDB
mysql -h $VELODB_FE_HOST -P 9030 -u $VELODB_USER -p$VELODB_PASSWORD -e "
SELECT email, plan FROM user_analytics.dim_users WHERE email = 'test.user@example.com';"
```

## Troubleshooting

### Replication Slot Issues

```bash
# Check existing slots
docker exec postgres psql -U labuser -d user_analytics -c "SELECT * FROM pg_replication_slots;"

# Drop a stuck slot
docker exec postgres psql -U labuser -d user_analytics -c "SELECT pg_drop_replication_slot('flink_dim_users_slot');"
```

### Jobs Not Running

```bash
# Check Flink logs for errors
docker logs flink-cdc 2>&1 | grep -i error | tail -20

# Restart Flink CDC
docker compose restart flink-cdc
```

### Stream Load Failures

Common errors:
- **401 Unauthorized**: Check VeloDB credentials in `.env`
- **Connection refused**: Check VELODB_FE_HOST and HTTP port
- **Table not found**: Run `flink/velodb_schema.sql` in VeloDB

## Configuration Files

| File | Purpose |
|------|---------|
| `flink/Dockerfile` | Flink image with CDC connectors |
| `flink/cdc-job.sql` | Flink SQL table definitions |
| `flink/start-cdc-job.sh` | Startup script |
| `flink/velodb_schema.sql` | VeloDB target schema |

## Next Steps

**[Module 3: Kafka Integration](./03-kafka-integration.md)** - Alternative streaming path (optional)

Or skip to:

**[Module 4: Superset BI](./04-superset-bi.md)** - Build analytics dashboards
