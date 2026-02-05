# Module 3: Kafka Integration with Doris Kafka Connector

This module demonstrates streaming data from Kafka to VeloDB using the Doris Kafka Connector.

## Architecture

```
                    ┌─────────────────────────────────────────────────────────┐
                    │                 DOCKER COMPOSE                           │
                    │                                                          │
   ┌──────────┐     │  ┌──────────┐    ┌──────────┐    ┌─────────────────┐   │
   │ Datagen  │─────┼─►│  Kafka   │───►│  Kafka   │───►│ VeloDB Cloud    │   │
   │          │     │  │ (topic:  │    │ Connect  │    │ (table:         │   │
   └──────────┘     │  │fact_events)   │(Doris Sink)   │kafka_fact_events)   │
                    │  └──────────┘    └──────────┘    └─────────────────┘   │
                    └─────────────────────────────────────────────────────────┘
```

## Why a Separate Table?

The Kafka path writes to `kafka_fact_events` instead of `fact_events` because:
- **Flink CDC already syncs `fact_events`** from PostgreSQL
- Writing to the same table would create **duplicates**
- Separate tables let you **compare both paths** side-by-side

## Step 1: Create Target Table in VeloDB

> ⚠️ **Critical**: The table must have `enable_unique_key_merge_on_write = false` for Kafka Connect compatibility.

```sql
USE user_analytics;

-- Kafka events table (separate from CDC path)
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

-- Verify table settings
SHOW CREATE TABLE kafka_fact_events;
-- Confirm: enable_unique_key_merge_on_write = false
```

## Step 2: Verify Kafka Services

Kafka services start automatically with `docker compose up`. Verify:

```bash
# Check all services are running
docker compose ps

# Expected output includes:
# kafka           ... Up (healthy)
# kafka-connect   ... Up (healthy)
# zookeeper       ... Up (healthy)

# List Kafka topics (auto-created by datagen)
docker exec kafka kafka-topics --list --bootstrap-server localhost:9092
# Expected: fact_events, fact_conversions
```

## Step 3: Check Kafka Connect Connector

The connector auto-registers on startup. Verify:

```bash
# List connectors
curl -s http://localhost:8083/connectors
# Expected: ["velodb-kafka-events-sink"]

# Check connector status
curl -s http://localhost:8083/connectors/velodb-kafka-events-sink/status | python3 -m json.tool
```

Expected status:
```json
{
    "name": "velodb-kafka-events-sink",
    "connector": { "state": "RUNNING" },
    "tasks": [{ "id": 0, "state": "RUNNING" }]
}
```

## Step 4: Manual Connector Registration (If Needed)

If the connector didn't auto-register, deploy manually:

```bash
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
        "doris.user": "admin",
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

## Configuration Reference

| Parameter | Description | Example |
|-----------|-------------|---------|
| `doris.urls` | VeloDB FE hostname | `cluster.velodb.io` |
| `doris.http.port` | HTTP/Stream Load port | `8080` |
| `doris.query.port` | MySQL protocol port | `9030` |
| `doris.database` | Target database | `user_analytics` |
| `doris.topic2table.map` | Topic-to-table mapping | `fact_events:kafka_fact_events` |
| `buffer.count.records` | Records before flush | `1000` |
| `buffer.flush.time` | Flush interval (seconds) | `10` |

> **Note**: Use `doris.topic2table.map` instead of `doris.table`. Format: `topic:table`

## Step 5: Verify Data Flow

### Check Kafka Messages

```bash
# View message count
docker exec kafka kafka-run-class kafka.tools.GetOffsetShell \
    --broker-list localhost:9092 --topic fact_events --time -1
```

### Check VeloDB Data

```sql
-- Count events from Kafka path
SELECT COUNT(*) FROM user_analytics.kafka_fact_events;

-- Compare both paths
SELECT 'fact_events (CDC)' as source, COUNT(*) as count
FROM user_analytics.fact_events
UNION ALL
SELECT 'kafka_fact_events (Kafka)', COUNT(*)
FROM user_analytics.kafka_fact_events;

-- View recent Kafka events
SELECT event_id, user_id, event_type, event_time
FROM user_analytics.kafka_fact_events
ORDER BY event_time DESC LIMIT 10;
```

## Troubleshooting

### Task FAILED: "stream load 2pc is unsupported for mow table"

**Cause**: Target table has `enable_unique_key_merge_on_write = true`

**Fix**: Recreate the table with merge-on-write disabled:
```sql
DROP TABLE IF EXISTS kafka_fact_events;
CREATE TABLE kafka_fact_events (...)
PROPERTIES ("enable_unique_key_merge_on_write" = "false");
```

Then restart the connector task:
```bash
curl -X POST http://localhost:8083/connectors/velodb-kafka-events-sink/tasks/0/restart
```

### Task FAILED: "table not found, tableName=null"

**Cause**: Using `doris.table` parameter instead of `doris.topic2table.map`

**Fix**: Delete and recreate connector with correct config:
```bash
curl -X DELETE http://localhost:8083/connectors/velodb-kafka-events-sink
# Then recreate with doris.topic2table.map parameter
```

### Connector Not Auto-Registering

Check logs:
```bash
docker logs kafka-connect 2>&1 | grep -i "registration\|connector\|error"
```

Register manually using Step 4 above.

### Connection Timeout

1. Verify VeloDB is accessible: `curl http://YOUR_HOST:8080/api/bootstrap`
2. Check IP whitelist in VeloDB Cloud Console
3. Increase timeout settings in connector config

## Connector Management

```bash
# Pause connector
curl -X PUT http://localhost:8083/connectors/velodb-kafka-events-sink/pause

# Resume connector
curl -X PUT http://localhost:8083/connectors/velodb-kafka-events-sink/resume

# Restart connector
curl -X POST http://localhost:8083/connectors/velodb-kafka-events-sink/restart

# Delete connector
curl -X DELETE http://localhost:8083/connectors/velodb-kafka-events-sink
```

## Next Steps

Continue to **[Module 4: Superset BI](./04-superset-bi.md)** to visualize your data.
