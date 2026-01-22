#!/bin/bash
set -e

echo "=========================================="
echo "VeloDB Customer Analytics Demo"
echo "=========================================="
echo ""
echo "Configuration:"
echo "  VELODB_HOST: ${VELODB_HOST}"
echo "  VELODB_PORT: ${VELODB_PORT}"
echo "  VELODB_USER: ${VELODB_USER}"
echo "  VELODB_DATABASE: ${VELODB_DATABASE}"
echo ""

# Generate Evidence connection.yaml from environment variables
echo "[SETUP] Generating Evidence connection configuration..."
mkdir -p /app/evidence/sources/velodb
cat > /app/evidence/sources/velodb/connection.yaml << EOF
name: velodb
type: mysql
options:
  host: ${VELODB_HOST}
  port: ${VELODB_PORT}
  user: ${VELODB_USER}
  password: ${VELODB_PASSWORD}
  database: ${VELODB_DATABASE}
EOF

# Generate Evidence source data from SQL queries
echo "[SETUP] Generating Evidence source data..."
cd /app/evidence
npm run sources --yes 2>&1 || echo "[WARN] Initial source generation had issues, will retry on first page load"

echo "[SETUP] Starting services..."
echo "  - Data generator (continuous events)"
echo "  - Evidence dashboard (http://localhost:3000)"
echo ""
echo "=========================================="

exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
