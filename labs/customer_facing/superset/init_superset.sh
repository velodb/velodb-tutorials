#!/bin/bash
set -e

echo "=== VeloDB Integration Lab - Superset Initialization ==="

# Wait for database to be ready
echo "Waiting for initialization..."
sleep 5

# Start Superset
echo "Starting Superset server on port 8088..."
exec superset run -h 0.0.0.0 -p 8088 --with-threads --reload
