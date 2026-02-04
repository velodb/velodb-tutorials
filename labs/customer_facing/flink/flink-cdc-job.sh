#!/bin/bash
#
# VeloDB Integration Lab - Flink CDC Job Script
#
# Syncs ALL 5 tables from PostgreSQL to VeloDB:
# - Dimension tables: dim_users, dim_features, dim_campaigns
# - Fact tables: fact_events, fact_conversions
#
# Prerequisites:
#   1. Download Flink CDC package from VeloDB documentation
#   2. Configure environment variables in .env file
#   3. Ensure PostgreSQL and VeloDB are accessible
#

set -e

# Load environment variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../.env"

if [ -f "$ENV_FILE" ]; then
    echo "Loading environment from $ENV_FILE"
    export $(cat "$ENV_FILE" | grep -v '^#' | xargs)
else
    echo "Warning: .env file not found at $ENV_FILE"
    echo "Please copy .env.example to .env and configure your settings"
    exit 1
fi

# Verify required variables
REQUIRED_VARS=(
    "POSTGRES_HOST"
    "POSTGRES_PORT"
    "POSTGRES_USER"
    "POSTGRES_PASSWORD"
    "POSTGRES_DB"
    "VELODB_FE_HOST"
    "VELODB_HTTP_PORT"
    "VELODB_QUERY_PORT"
    "VELODB_USER"
    "VELODB_PASSWORD"
    "VELODB_DATABASE"
)

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo "Error: Required variable $var is not set"
        exit 1
    fi
done

# Flink CDC directory (adjust this path as needed)
FLINK_CDC_HOME="${FLINK_CDC_HOME:-$HOME/flink-cdc}"

if [ ! -d "$FLINK_CDC_HOME" ]; then
    echo "Error: Flink CDC home directory not found: $FLINK_CDC_HOME"
    echo ""
    echo "Please download the Flink CDC package:"
    echo "  curl -O https://apache-doris-releases.oss-accelerate.aliyuncs.com/extention/flink-1.17.2-with-doris-connector.tar.gz"
    echo "  tar -xzf flink-1.17.2-with-doris-connector.tar.gz"
    echo "  export FLINK_CDC_HOME=\$(pwd)/flink-1.17.2-with-doris-connector"
    exit 1
fi

echo "================================================"
echo "VeloDB Integration Lab - Flink CDC Job"
echo "================================================"
echo "PostgreSQL: ${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"
echo "VeloDB:     ${VELODB_FE_HOST}:${VELODB_HTTP_PORT}"
echo "Database:   ${VELODB_DATABASE}"
echo "================================================"

# All 5 tables to sync
TABLES_PATTERN="public\\.dim_users|public\\.dim_features|public\\.dim_campaigns|public\\.fact_events|public\\.fact_conversions"

echo "Starting Flink CDC synchronization..."
echo "Tables: dim_users, dim_features, dim_campaigns, fact_events, fact_conversions"
echo ""

# Run the Flink CDC job
cd "$FLINK_CDC_HOME"

./bin/flink-cdc.sh \
    --postgres-conf hostname="${POSTGRES_HOST}" \
    --postgres-conf port="${POSTGRES_PORT}" \
    --postgres-conf username="${POSTGRES_USER}" \
    --postgres-conf password="${POSTGRES_PASSWORD}" \
    --postgres-conf database-name="${POSTGRES_DB}" \
    --postgres-conf schema-name=public \
    --postgres-conf slot.name=flink_cdc_lab_slot \
    --postgres-conf decoding.plugin.name=pgoutput \
    --including-tables "${TABLES_PATTERN}" \
    --doris-conf fenodes="${VELODB_FE_HOST}:${VELODB_HTTP_PORT}" \
    --doris-conf jdbc-url="jdbc:mysql://${VELODB_FE_HOST}:${VELODB_QUERY_PORT}" \
    --doris-conf username="${VELODB_USER}" \
    --doris-conf password="${VELODB_PASSWORD}" \
    --doris-conf sink.label-prefix=pg_cdc_lab

echo ""
echo "Flink CDC job submitted successfully!"
echo "Monitor the job at: http://localhost:8081 (if Flink UI is enabled)"
