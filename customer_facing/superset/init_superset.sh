#!/bin/bash
set -e

echo "[INIT] Initializing Superset..."

# Check if already initialized
if [ -f "/app/superset.db" ]; then
    echo "[INIT] Superset already initialized, skipping..."
    exit 0
fi

# Initialize database
echo "[INIT] Running database migrations..."
superset db upgrade

# Create admin user
echo "[INIT] Creating admin user..."
superset fab create-admin \
    --username "${SUPERSET_ADMIN_USER:-admin}" \
    --firstname Admin \
    --lastname User \
    --email admin@localhost \
    --password "${SUPERSET_ADMIN_PASSWORD:-admin}"

# Initialize Superset
echo "[INIT] Initializing roles and permissions..."
superset init

echo "[INIT] Superset initialization complete!"
