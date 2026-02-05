# VeloDB Real-Time Data Integration Lab

A hands-on lab for system integrators demonstrating real-time data pipelines into VeloDB Cloud using PostgreSQL CDC, Flink, Kafka, and Apache Superset.

## Architecture Overview

```
┌────────────────────────────────────────────────────────────────────────────────────┐
│                           DOCKER COMPOSE (Local)                                    │
├────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│                         PATH 1: CDC (Database Changes)                              │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐                      │
│  │   Datagen    │ ---> │  PostgreSQL  │ ---> │  Flink CDC   │ ──┐                  │
│  │ (Mock Data)  │      │ (5 Tables)   │      │ (Connector)  │   │                  │
│  └──────┬───────┘      └──────────────┘      └──────────────┘   │                  │
│         │                                                        │                  │
│         │              PATH 2: Streaming (Events)                │                  │
│         │              ┌──────────────┐      ┌──────────────┐   │                  │
│         └───────────-> │    Kafka     │ ---> │ Kafka Connect│ ──┤                  │
│                        │  (Events)    │      │ (Doris Sink) │   │                  │
│                        └──────────────┘      └──────────────┘   │                  │
│                                                                  │ Stream Load     │
└──────────────────────────────────────────────────────────────────┼──────────────────┘
                                                                   ▼
                                                         ┌──────────────────┐
                                                         │   VeloDB Cloud   │
                                                         │  (user_analytics)│
                                                         └────────┬─────────┘
                                                                  │
                                                                  ▼
                                                         ┌──────────────────┐
                                                         │ Apache Superset  │
                                                         │  (BI Dashboard)  │
                                                         └──────────────────┘
```

## Data Model

| Table | Type | Source | Description |
|-------|------|--------|-------------|
| `dim_users` | Dimension | Flink CDC | User profiles with plan/country/industry |
| `dim_features` | Dimension | Flink CDC | Product features by tier |
| `dim_campaigns` | Dimension | Flink CDC | Marketing campaigns and channels |
| `fact_events` | Fact | Flink CDC | User behavior events (~5/sec) |
| `fact_conversions` | Fact | Flink CDC | Revenue and conversion events |
| `kafka_fact_events` | Fact | Kafka Connect | Same events via Kafka path (demo) |

## What You Will Learn

1. **PostgreSQL CDC Integration** - Capture database changes in real-time using Flink CDC
2. **Kafka Streaming Integration** - Stream events via Kafka Connect Doris Sink
3. **VeloDB Stream Load** - High-throughput data ingestion via Flink Doris Connector
4. **BI Dashboard Setup** - Visualize analytics with Apache Superset

## Prerequisites

- VeloDB Cloud account with active cluster
- Docker and Docker Compose installed
- MySQL client (for VeloDB connectivity testing)

## Quick Start

```bash
# 1. Navigate to lab directory
cd labs/customer_facing

# 2. Copy and configure environment
cp .env.example .env
# Edit .env with your VeloDB Cloud credentials:
#   VELODB_FE_HOST=your-cluster.velodb.io
#   VELODB_USER=admin
#   VELODB_PASSWORD=your_password

# 3. IMPORTANT: Create VeloDB target tables FIRST
#    Copy contents of flink/velodb_schema.sql
#    Paste and run in VeloDB Cloud SQL Editor
#    This creates the database and all 6 tables

# 4. Start all services
docker compose up -d

# 5. Verify services are running
docker compose ps

# 6. Watch data flowing (wait ~30 seconds)
docker logs -f datagen          # See events being generated
docker logs -f flink-cdc        # See CDC sync status
docker logs -f kafka-connect    # See Kafka connector status

# 7. Access dashboards
open http://localhost:8088   # Superset (admin/admin)
open http://localhost:8081   # Flink Web UI
```

## Services & Ports

| Service | Port | Description |
|---------|------|-------------|
| PostgreSQL | 5432 | Source database (labuser/labpass) |
| Flink Web UI | 8081 | CDC job monitoring |
| Superset | 8088 | BI dashboard (admin/admin) |
| Kafka | 9092 | Event streaming |
| Kafka Connect | 8083 | Doris sink connector REST API |

## Directory Structure

```
customer_facing/
├── README.md                 # This file
├── TUTORIAL.md               # Comprehensive step-by-step tutorial
├── docker-compose.yml        # All services orchestration
├── .env.example              # Environment template
├── quick-start.sh            # Automated setup script
├── docs/                     # Detailed module guides
│   ├── 01-setup.md
│   ├── 02-postgres-cdc.md
│   ├── 03-kafka-integration.md
│   ├── 04-superset-bi.md
│   ├── 05-verification.md
│   └── user-analytics-1.png  # Dashboard screenshot
├── datagen/                  # Data generation
│   ├── Dockerfile
│   ├── continuous_datagen.py # Generates events to PostgreSQL + Kafka
│   ├── init_postgres.sql     # Schema and seed data
│   └── requirements.txt
├── flink/                    # Flink CDC configuration
│   ├── Dockerfile
│   ├── cdc-job.sql           # Flink SQL job definitions
│   ├── start-cdc-job.sh      # Docker entrypoint
│   └── velodb_schema.sql     # VeloDB target schema (run FIRST!)
├── kafka-connect/            # Kafka Connect configuration
│   ├── Dockerfile            # Doris sink connector setup
│   └── doris-sink.json       # Connector configuration
└── superset/                 # Superset configuration
    ├── Dockerfile
    ├── superset_config.py
    └── init_superset.sh
```

## Verification

```bash
# Check Flink CDC jobs (should show 5 RUNNING jobs)
curl -s http://localhost:8081/jobs/overview | python3 -c "
import sys, json
for job in json.load(sys.stdin)['jobs']:
    print(f\"{job['state']:10} {job['name'].split('.')[-1]}\")"

# Check Kafka Connect connector
curl -s http://localhost:8083/connectors/velodb-kafka-events-sink/status | python3 -m json.tool

# Check PostgreSQL source
docker exec postgres psql -U labuser -d user_analytics \
  -c "SELECT COUNT(*) FROM fact_events;"

# Check VeloDB target - both tables should have data
mysql -h YOUR_HOST -P 9030 -u admin -p -e "
  SELECT 'fact_events (CDC)' as source, COUNT(*) as count FROM user_analytics.fact_events
  UNION ALL
  SELECT 'kafka_fact_events (Kafka)' as source, COUNT(*) as count FROM user_analytics.kafka_fact_events;"
```

## Troubleshooting

### "Access denied for user 'admin@x.x.x.x'"
Your IP is not whitelisted in VeloDB Cloud:
1. Find your public IP: `curl -s ifconfig.me`
2. Go to VeloDB Cloud Console → Cluster → Network Settings
3. Add your IP to the whitelist (or use `0.0.0.0/0` for testing)

### Kafka Connect task FAILED with "2pc unsupported for mow table"
The `kafka_fact_events` table has `enable_unique_key_merge_on_write = true`. Recreate it:
```sql
DROP TABLE IF EXISTS kafka_fact_events;
CREATE TABLE kafka_fact_events (...)
PROPERTIES ("enable_unique_key_merge_on_write" = "false");
```

### Kafka Connect task FAILED with "table not found, tableName=null"
The connector config uses wrong parameter. Use `doris.topic2table.map` instead of `doris.table`:
```json
"doris.topic2table.map": "fact_events:kafka_fact_events"
```

### Flink CDC jobs stuck in SCHEDULED state
TaskManager needs more slots. Check `flink/start-cdc-job.sh` includes:
```bash
echo "taskmanager.numberOfTaskSlots: 10" >> /opt/flink/conf/flink-conf.yaml
```

### No data in VeloDB after starting
1. Check Flink logs: `docker logs flink-cdc | grep -i "error\|success"`
2. Verify VeloDB tables exist: Run `flink/velodb_schema.sql` first
3. Check IP whitelist (see above)

## Documentation

- **[Full Tutorial](./TUTORIAL.md)** - Complete hands-on guide
- **[VeloDB CDC Documentation](https://docs.velodb.io/cloud/integration/data-source/postgres-cdc)** - Official reference

## Support

For questions or issues, contact your VeloDB solutions architect.
