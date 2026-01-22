#!/bin/bash
set -e

echo "=========================================="
echo "VeloDB Customer Analytics Demo (Superset)"
echo "=========================================="
echo ""
echo "Configuration:"
echo "  VELODB_HOST: ${VELODB_HOST}"
echo "  VELODB_PORT: ${VELODB_PORT}"
echo "  VELODB_USER: ${VELODB_USER}"
echo "  VELODB_DATABASE: ${VELODB_DATABASE}"
echo ""

# Initialize Superset if needed
/app/init_superset.sh

# Create database and schema in VeloDB
echo "[SETUP] Creating database and schema in VeloDB..."
python3 /app/datagen/setup_schema.py \
  --host "${VELODB_HOST}" \
  --port "${VELODB_PORT}" \
  --user "${VELODB_USER}" \
  --password "${VELODB_PASSWORD}" \
  --database "${VELODB_DATABASE}" || echo "[WARN] Schema setup had issues, continuing..."

# Setup dashboard using ORM (direct database access, no API needed)
echo "[SETUP] Creating database connection, datasets, and dashboard..."
python3 /app/setup_via_orm.py || echo "[WARN] Dashboard setup had issues, continuing..."

# Seed 30 days of historical data for presentation-ready charts
echo "[SETUP] Seeding 30 days of historical data for charts..."
python3 /app/seed_history.py \
  --host "${VELODB_HOST}" \
  --port "${VELODB_PORT}" \
  --user "${VELODB_USER}" \
  --password "${VELODB_PASSWORD}" \
  --database "${VELODB_DATABASE}" \
  --days 30 || echo "[WARN] Historical data seeding had issues, continuing..."

echo ""
echo "[SETUP] Starting services..."
echo "  - Data generator (continuous events)"
echo "  - Superset dashboard (http://localhost:8088)"
echo ""
echo "Dashboard URL: http://localhost:8088/superset/dashboard/velodb-analytics/"
echo "Login: admin / admin"
echo ""
echo "=========================================="

# Start supervisord (runs both Superset and datagen)
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
