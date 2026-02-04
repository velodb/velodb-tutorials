#!/bin/bash
#
# Flink CDC Job Startup Script
# Waits for dependencies and starts the CDC sync job
#

set -e

echo "=========================================="
echo "Flink CDC Job - PostgreSQL to VeloDB"
echo "=========================================="

# Environment variables (with defaults)
POSTGRES_HOST="${POSTGRES_HOST:-postgres}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-labuser}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-labpass}"
POSTGRES_DB="${POSTGRES_DB:-user_analytics}"

VELODB_FE_HOST="${VELODB_FE_HOST:-localhost}"
VELODB_HTTP_PORT="${VELODB_HTTP_PORT:-8030}"
VELODB_USER="${VELODB_USER:-admin}"
VELODB_PASSWORD="${VELODB_PASSWORD:-}"
VELODB_DATABASE="${VELODB_DATABASE:-user_analytics}"

echo "PostgreSQL: ${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"
echo "VeloDB: ${VELODB_FE_HOST}:${VELODB_HTTP_PORT}/${VELODB_DATABASE}"

# Wait for PostgreSQL
echo ""
echo "[1/4] Waiting for PostgreSQL..."
MAX_RETRIES=60
RETRY=0
until pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" > /dev/null 2>&1; do
    RETRY=$((RETRY + 1))
    if [ $RETRY -ge $MAX_RETRIES ]; then
        echo "ERROR: PostgreSQL not ready after $MAX_RETRIES attempts"
        exit 1
    fi
    echo "  Waiting for PostgreSQL... ($RETRY/$MAX_RETRIES)"
    sleep 2
done
echo "  PostgreSQL is ready!"

# Wait for PostgreSQL to have seed data
echo ""
echo "[2/4] Waiting for seed data..."
RETRY=0
until PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT COUNT(*) FROM dim_users" 2>/dev/null | grep -q "[1-9]"; do
    RETRY=$((RETRY + 1))
    if [ $RETRY -ge $MAX_RETRIES ]; then
        echo "ERROR: Seed data not found after $MAX_RETRIES attempts"
        exit 1
    fi
    echo "  Waiting for seed data... ($RETRY/$MAX_RETRIES)"
    sleep 2
done
echo "  Seed data is ready!"

# Check VeloDB connectivity
echo ""
echo "[3/4] Checking VeloDB connectivity..."
RETRY=0
until curl -s -o /dev/null -w "%{http_code}" "http://${VELODB_FE_HOST}:${VELODB_HTTP_PORT}/api/bootstrap" 2>/dev/null | grep -q "200\|401\|403"; do
    RETRY=$((RETRY + 1))
    if [ $RETRY -ge $MAX_RETRIES ]; then
        echo "WARNING: Cannot reach VeloDB at ${VELODB_FE_HOST}:${VELODB_HTTP_PORT}"
        echo "Make sure VeloDB is accessible and tables are created."
        echo "Continuing anyway..."
        break
    fi
    echo "  Waiting for VeloDB... ($RETRY/$MAX_RETRIES)"
    sleep 2
done
echo "  VeloDB check complete!"

# Substitute environment variables in SQL file
echo ""
echo "[4/4] Preparing CDC job..."
cd /opt/flink

# Create the processed SQL file with environment variables substituted
envsubst < /opt/flink/cdc-job.sql > /opt/flink/cdc-job-processed.sql

echo "  SQL job file prepared"

# Configure Flink for 10 task slots (5 jobs × 2 tasks each)
echo ""
echo "Configuring Flink..."
echo "taskmanager.numberOfTaskSlots: 10" >> /opt/flink/conf/flink-conf.yaml
echo "parallelism.default: 1" >> /opt/flink/conf/flink-conf.yaml

# Start Flink cluster in the background
echo ""
echo "Starting Flink cluster..."
/opt/flink/bin/start-cluster.sh

# Wait for Flink to be ready
sleep 10

# Submit the SQL job
echo ""
echo "Submitting CDC job to Flink..."
echo "=========================================="

# Use Flink SQL client to execute the job
/opt/flink/bin/sql-client.sh -f /opt/flink/cdc-job-processed.sql &

echo ""
echo "CDC job submitted!"
echo "=========================================="
echo "Syncing tables:"
echo "  - dim_users"
echo "  - dim_features"
echo "  - dim_campaigns"
echo "  - fact_events"
echo "  - fact_conversions"
echo "=========================================="
echo ""
echo "Flink Web UI: http://localhost:8081"
echo ""

# Keep the container running
tail -f /opt/flink/log/*.log
