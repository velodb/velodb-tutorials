# VeloDB Real-Time Data Integration Lab

A hands-on lab for system integrators demonstrating real-time data pipelines into VeloDB Cloud using PostgreSQL CDC, Flink, and Apache Superset.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         DOCKER COMPOSE (Local)                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐                   │
│  │   Datagen    │ ---> │  PostgreSQL  │ ---> │  Flink CDC   │                   │
│  │ (Mock Data)  │      │ (5 Tables)   │      │ (Connector)  │                   │
│  └──────────────┘      └──────────────┘      └──────┬───────┘                   │
│                                                      │                           │
└──────────────────────────────────────────────────────┼───────────────────────────┘
                                                       │ Stream Load
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

## Data Model: 5-Table Star Schema

| Table | Type | Description |
|-------|------|-------------|
| `dim_users` | Dimension | User profiles with plan/country/industry |
| `dim_features` | Dimension | Product features by tier |
| `dim_campaigns` | Dimension | Marketing campaigns and channels |
| `fact_events` | Fact | User behavior events (~5/sec) |
| `fact_conversions` | Fact | Revenue and conversion events |

## What You Will Learn

1. **PostgreSQL CDC Integration** - Capture database changes in real-time using Flink CDC
2. **VeloDB Stream Load** - High-throughput data ingestion via Flink Doris Connector
3. **BI Dashboard Setup** - Visualize analytics with Apache Superset

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
# Edit .env with your VeloDB Cloud credentials

# 3. Create VeloDB target tables (run in VeloDB SQL Editor)
#    Use the SQL from: flink/velodb_schema.sql

# 4. Start all services
docker compose up -d

# 5. Verify services
docker compose ps

# 6. Access Superset dashboard
open http://localhost:8088   # admin/admin
```

## Services & Ports

| Service | Port | Description |
|---------|------|-------------|
| PostgreSQL | 5432 | Source database (labuser/labpass) |
| Flink Web UI | 8081 | CDC job monitoring |
| Superset | 8088 | BI dashboard (admin/admin) |

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
│   ├── continuous_datagen.py # Generates events to PostgreSQL
│   ├── init_postgres.sql     # Schema and seed data
│   └── requirements.txt
├── flink/                    # Flink CDC configuration
│   ├── Dockerfile
│   ├── cdc-job.sql           # Flink SQL job definitions
│   ├── start-cdc-job.sh      # Docker entrypoint
│   └── velodb_schema.sql     # VeloDB target schema
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

# Check PostgreSQL source
docker exec postgres psql -U labuser -d user_analytics \
  -c "SELECT COUNT(*) FROM fact_events;"

# Check VeloDB target
mysql -h YOUR_HOST -P 9030 -u admin -p \
  -e "SELECT COUNT(*) FROM user_analytics.fact_events;"
```

## Documentation

- **[Full Tutorial](./TUTORIAL.md)** - Complete hands-on guide
- **[VeloDB CDC Documentation](https://docs.velodb.io/cloud/integration/data-source/postgres-cdc)** - Official reference

## Support

For questions or issues, contact your VeloDB solutions architect.
