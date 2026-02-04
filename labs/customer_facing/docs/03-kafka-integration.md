# Module 3: Kafka Integration with Doris Kafka Connector

This module demonstrates streaming data from Kafka to VeloDB using the Doris Kafka Connector.

## Architecture

```
Applications/IoT  →  Kafka Topics  →  Kafka Connect  →  VeloDB Cloud
       ↓                  ↓               ↓                  ↓
  Event Stream      [user_events]    Doris Sink       [user_events]
  Metrics Stream    [app_metrics]    Connector        [app_metrics]
```

## Step 1: Create Kafka Topics

Create the required Kafka topics:

```bash
# Create user events topic
docker exec -it kafka kafka-topics --create \
    --bootstrap-server localhost:9092 \
    --topic user_events \
    --partitions 3 \
    --replication-factor 1

# Create app metrics topic
docker exec -it kafka kafka-topics --create \
    --bootstrap-server localhost:9092 \
    --topic app_metrics \
    --partitions 3 \
    --replication-factor 1

# Verify topics
docker exec -it kafka kafka-topics --list --bootstrap-server localhost:9092
```

## Step 2: Create Target Tables in VeloDB

Connect to VeloDB SQL Editor:

```sql
USE user_analytics;

-- User events table (append-only for event streaming)
CREATE TABLE IF NOT EXISTS user_events (
    event_id VARCHAR(64),
    user_id INT,
    event_type VARCHAR(50),
    event_name VARCHAR(100),
    page_url VARCHAR(500),
    referrer VARCHAR(500),
    device_type VARCHAR(50),
    browser VARCHAR(100),
    country VARCHAR(100),
    city VARCHAR(100),
    session_id VARCHAR(64),
    properties JSON,
    event_time DATETIME,
    ingested_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
DUPLICATE KEY(event_id, user_id, event_type)
DISTRIBUTED BY HASH(user_id) BUCKETS 4
PROPERTIES (
    "replication_num" = "1"
);

-- Create inverted index for fast filtering
CREATE INDEX idx_event_type ON user_events(event_type) USING INVERTED;
CREATE INDEX idx_event_time ON user_events(event_time) USING INVERTED;

-- App metrics table (aggregation-friendly)
CREATE TABLE IF NOT EXISTS app_metrics (
    metric_id VARCHAR(64),
    metric_name VARCHAR(100),
    metric_value DOUBLE,
    metric_unit VARCHAR(20),
    service_name VARCHAR(100),
    host VARCHAR(255),
    environment VARCHAR(20),
    tags JSON,
    timestamp DATETIME
)
DUPLICATE KEY(metric_id, metric_name, service_name)
DISTRIBUTED BY HASH(service_name) BUCKETS 4
PROPERTIES (
    "replication_num" = "1"
);

-- Verify tables
SHOW TABLES;
DESC user_events;
DESC app_metrics;
```

## Step 3: Configure Doris Kafka Connector

Create the connector configuration files:

### User Events Connector

```bash
cat > kafka-connect/user-events-sink.json << 'EOF'
{
    "name": "velodb-user-events-sink",
    "config": {
        "connector.class": "org.apache.doris.kafka.connector.DorisSinkConnector",
        "tasks.max": "1",
        "topics": "user_events",
        "doris.urls": "${VELODB_FE_HOST}",
        "doris.http.port": "8030",
        "doris.query.port": "9030",
        "doris.user": "${VELODB_USER}",
        "doris.password": "${VELODB_PASSWORD}",
        "doris.database": "user_analytics",
        "doris.table": "user_events",
        "key.converter": "org.apache.kafka.connect.storage.StringConverter",
        "value.converter": "org.apache.kafka.connect.json.JsonConverter",
        "value.converter.schemas.enable": "false",
        "buffer.count.records": "10000",
        "buffer.flush.time": "60",
        "buffer.size.bytes": "5000000",
        "jmx": "false"
    }
}
EOF
```

### App Metrics Connector

```bash
cat > kafka-connect/app-metrics-sink.json << 'EOF'
{
    "name": "velodb-app-metrics-sink",
    "config": {
        "connector.class": "org.apache.doris.kafka.connector.DorisSinkConnector",
        "tasks.max": "1",
        "topics": "app_metrics",
        "doris.urls": "${VELODB_FE_HOST}",
        "doris.http.port": "8030",
        "doris.query.port": "9030",
        "doris.user": "${VELODB_USER}",
        "doris.password": "${VELODB_PASSWORD}",
        "doris.database": "user_analytics",
        "doris.table": "app_metrics",
        "key.converter": "org.apache.kafka.connect.storage.StringConverter",
        "value.converter": "org.apache.kafka.connect.json.JsonConverter",
        "value.converter.schemas.enable": "false",
        "buffer.count.records": "10000",
        "buffer.flush.time": "30",
        "buffer.size.bytes": "5000000",
        "jmx": "false"
    }
}
EOF
```

## Step 4: Deploy Connectors

### Check Kafka Connect is Ready

```bash
curl -s http://localhost:8083/ | jq .
```

Expected output:
```json
{
  "version": "3.x.x",
  "commit": "...",
  "kafka_cluster_id": "..."
}
```

### Deploy User Events Connector

```bash
# Substitute environment variables and deploy
envsubst < kafka-connect/user-events-sink.json | \
curl -X POST http://localhost:8083/connectors \
    -H "Content-Type: application/json" \
    -d @-
```

### Deploy App Metrics Connector

```bash
envsubst < kafka-connect/app-metrics-sink.json | \
curl -X POST http://localhost:8083/connectors \
    -H "Content-Type: application/json" \
    -d @-
```

### Verify Connector Status

```bash
# List all connectors
curl -s http://localhost:8083/connectors | jq .

# Check user events connector status
curl -s http://localhost:8083/connectors/velodb-user-events-sink/status | jq .

# Check app metrics connector status
curl -s http://localhost:8083/connectors/velodb-app-metrics-sink/status | jq .
```

Both connectors should show:
```json
{
  "state": "RUNNING",
  "worker_id": "..."
}
```

## Step 5: Produce Test Messages

### Manual Test - User Events

```bash
# Produce a test event
docker exec -it kafka kafka-console-producer \
    --bootstrap-server localhost:9092 \
    --topic user_events << 'EOF'
{"event_id":"evt-001","user_id":1,"event_type":"page_view","event_name":"homepage_view","page_url":"/home","device_type":"desktop","browser":"Chrome","country":"US","city":"San Francisco","session_id":"sess-abc123","properties":{"referrer":"google.com"},"event_time":"2024-01-15 10:30:00"}
EOF
```

### Manual Test - App Metrics

```bash
docker exec -it kafka kafka-console-producer \
    --bootstrap-server localhost:9092 \
    --topic app_metrics << 'EOF'
{"metric_id":"met-001","metric_name":"api_latency_ms","metric_value":45.2,"metric_unit":"ms","service_name":"user-service","host":"pod-01","environment":"production","tags":{"endpoint":"/api/users"},"timestamp":"2024-01-15 10:30:00"}
EOF
```

## Step 6: Start Continuous Data Generation

Start the Kafka data generator:

```bash
# Start generating user events (5 events/second)
docker exec -d datagen python /app/kafka_datagen.py \
    --topic user_events \
    --rate 5 \
    --type events

# Start generating app metrics (10 metrics/second)
docker exec -d datagen python /app/kafka_datagen.py \
    --topic app_metrics \
    --rate 10 \
    --type metrics
```

## Step 7: Verify Data in VeloDB

### Check Event Counts

```sql
USE user_analytics;

-- Total events
SELECT COUNT(*) as total_events FROM user_events;

-- Events by type
SELECT
    event_type,
    COUNT(*) as count
FROM user_events
GROUP BY event_type
ORDER BY count DESC;

-- Recent events
SELECT
    event_id,
    user_id,
    event_type,
    page_url,
    event_time
FROM user_events
ORDER BY event_time DESC
LIMIT 10;
```

### Check Metrics

```sql
-- Total metrics
SELECT COUNT(*) as total_metrics FROM app_metrics;

-- Metrics by service
SELECT
    service_name,
    metric_name,
    AVG(metric_value) as avg_value,
    MAX(metric_value) as max_value,
    COUNT(*) as count
FROM app_metrics
GROUP BY service_name, metric_name
ORDER BY count DESC;

-- Recent metrics
SELECT
    metric_name,
    metric_value,
    service_name,
    timestamp
FROM app_metrics
ORDER BY timestamp DESC
LIMIT 10;
```

### Real-Time Analytics Query

```sql
-- User activity in the last 5 minutes
SELECT
    DATE_FORMAT(event_time, '%Y-%m-%d %H:%i:00') as minute,
    event_type,
    COUNT(*) as events,
    COUNT(DISTINCT user_id) as unique_users
FROM user_events
WHERE event_time >= NOW() - INTERVAL 5 MINUTE
GROUP BY minute, event_type
ORDER BY minute DESC;
```

## Step 8: Monitor Connector Performance

### View Consumer Lag

```bash
docker exec -it kafka kafka-consumer-groups \
    --bootstrap-server localhost:9092 \
    --describe \
    --group connect-velodb-user-events-sink
```

### Connector Metrics

```bash
# Get connector tasks
curl -s http://localhost:8083/connectors/velodb-user-events-sink/tasks | jq .

# Get task status
curl -s http://localhost:8083/connectors/velodb-user-events-sink/tasks/0/status | jq .
```

## Connector Management

### Pause Connector

```bash
curl -X PUT http://localhost:8083/connectors/velodb-user-events-sink/pause
```

### Resume Connector

```bash
curl -X PUT http://localhost:8083/connectors/velodb-user-events-sink/resume
```

### Restart Connector

```bash
curl -X POST http://localhost:8083/connectors/velodb-user-events-sink/restart
```

### Delete Connector

```bash
curl -X DELETE http://localhost:8083/connectors/velodb-user-events-sink
```

## Troubleshooting

### Connector in FAILED State

```bash
# Check detailed error
curl -s http://localhost:8083/connectors/velodb-user-events-sink/status | jq '.tasks[0].trace'
```

### JsonConverter Schema Error

If you see schema-related errors, ensure:
```json
"value.converter.schemas.enable": "false"
```

### Connection Timeout to VeloDB

1. Verify VeloDB cluster is accessible
2. Check firewall/IP whitelist
3. Increase timeout settings:
```json
"doris.request.connect.timeout.ms": "30000",
"doris.request.read.timeout.ms": "30000"
```

### High Consumer Lag

Increase parallelism:
```json
"tasks.max": "3"
```

Or increase buffer settings:
```json
"buffer.count.records": "50000",
"buffer.flush.time": "120"
```

## Configuration Reference

| Parameter | Description | Default |
|-----------|-------------|---------|
| `doris.urls` | FE node addresses | Required |
| `doris.http.port` | HTTP port | 8030 |
| `doris.query.port` | MySQL protocol port | 9030 |
| `buffer.count.records` | Records before flush | 50000 |
| `buffer.flush.time` | Flush interval (sec) | 120 |
| `buffer.size.bytes` | Buffer size limit | 5MB |
| `tasks.max` | Parallel tasks | 1 |

## Next Steps

Continue to **[Module 4: Superset BI](./04-superset-bi.md)** to visualize your data.
