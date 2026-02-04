# Module 1: Environment Setup

This module guides you through setting up the lab environment for real-time data integration with VeloDB Cloud.

## Prerequisites

### VeloDB Cloud Account

1. Log in to [VeloDB Cloud Console](https://cloud.velodb.io)
2. Ensure you have an active cluster
3. Note down the following connection details:
   - **FE Host**: Your cluster's Frontend node address
   - **HTTP Port**: 8080 (for Stream Load)
   - **Query Port**: 9030 (for SQL queries)
   - **Username**: Your database user (default: admin)
   - **Password**: Your database password

### Local Environment

Ensure you have the following installed:

```bash
# Check Docker
docker --version
# Expected: Docker version 20.x or higher

# Check Docker Compose
docker compose version
# Expected: Docker Compose version v2.x or higher

# Check MySQL client (for VeloDB connectivity)
mysql --version
# Expected: mysql Ver 8.x or compatible
```

## Step 1: Configure Environment Variables

Create a `.env` file from the template:

```bash
cd labs/customer_facing

# Copy template
cp .env.example .env

# Edit with your VeloDB credentials
nano .env  # or use your preferred editor
```

Update these required values in `.env`:

```bash
# VeloDB Cloud Connection (REQUIRED)
VELODB_FE_HOST=your-cluster-hostname.velodb.io
VELODB_HTTP_PORT=8080
VELODB_QUERY_PORT=9030
VELODB_USER=admin
VELODB_PASSWORD=your_secure_password
VELODB_DATABASE=user_analytics
```

> **Note**: The PostgreSQL settings can remain at defaults for the local Docker environment.

## Step 2: Create Target Database in VeloDB

Connect to VeloDB Cloud SQL Editor and create the target schema:

```sql
-- Create the database
CREATE DATABASE IF NOT EXISTS user_analytics;
USE user_analytics;

-- Verify creation
SHOW DATABASES LIKE 'user_analytics';
```

Then run the full schema from `flink/velodb_schema.sql`:

```sql
-- This creates all 5 tables:
-- dim_users, dim_features, dim_campaigns, fact_events, fact_conversions

-- Example: dim_users table
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

-- See flink/velodb_schema.sql for complete schema
```

## Step 3: Configure Network Access

If your VeloDB cluster has IP whitelisting enabled:

1. Find your public IP:
   ```bash
   curl -s ifconfig.me
   ```

2. Go to VeloDB Cloud Console → **Cluster Settings** → **Network**

3. Add your IP to the whitelist (or set to "Anywhere" for testing)

## Step 4: Start Docker Services

Launch all services:

```bash
# Start all services
docker compose up -d

# Verify services are running
docker compose ps
```

Expected output:
```
NAME        STATUS                   PORTS
datagen     Up
flink-cdc   Up                       6123/tcp, 0.0.0.0:8081->8081/tcp
postgres    Up (healthy)             0.0.0.0:5432->5432/tcp
superset    Up (healthy)             0.0.0.0:8088->8088/tcp
```

## Step 5: Verify Service Health

### Check PostgreSQL

```bash
docker exec postgres psql -U labuser -d user_analytics -c "SELECT COUNT(*) FROM dim_users;"
```

Expected: Should show 10 seed users.

### Check Flink CDC Jobs

```bash
curl -s http://localhost:8081/jobs/overview | python3 -c "
import sys, json
for job in json.load(sys.stdin)['jobs']:
    print(f\"{job['state']:10} {job['name'].split('.')[-1]}\")"
```

Expected: 5 jobs in RUNNING state.

### Check VeloDB Connectivity

```bash
mysql -h $VELODB_FE_HOST -P 9030 -u $VELODB_USER -p -e "SHOW DATABASES;"
```

### Check Superset

Open http://localhost:8088 in your browser.
- Username: `admin`
- Password: `admin`

## Troubleshooting

### Docker Services Won't Start

```bash
# Check logs for specific service
docker compose logs flink-cdc
docker compose logs postgres

# Restart all services
docker compose down && docker compose up -d
```

### Cannot Connect to VeloDB

1. Verify credentials in `.env` file
2. Check IP whitelist in VeloDB Console
3. Ensure cluster is in "Running" state
4. Test HTTP endpoint:
   ```bash
   curl -s "http://$VELODB_FE_HOST:8080/api/bootstrap"
   ```

### Flink Jobs Not Running

```bash
# Check Flink logs
docker logs flink-cdc | tail -50

# Look for errors
docker logs flink-cdc 2>&1 | grep -i error
```

### Port Conflicts

If ports are already in use:

```bash
# Find processes using ports
lsof -i :5432  # PostgreSQL
lsof -i :8081  # Flink Web UI
lsof -i :8088  # Superset

# Or modify ports in docker-compose.yml
```

## Next Steps

Once all services are running and VeloDB is accessible, proceed to:

**[Module 2: PostgreSQL CDC](./02-postgres-cdc.md)** - Understand the CDC pipeline
