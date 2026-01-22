#!/bin/sh
set -e

# Validate required environment variables
if [ -z "$VELODB_HOST" ]; then
    echo "Error: VELODB_HOST is required"
    exit 1
fi

if [ -z "$VELODB_USER" ]; then
    echo "Error: VELODB_USER is required"
    exit 1
fi

if [ -z "$VELODB_PASSWORD" ]; then
    echo "Error: VELODB_PASSWORD is required"
    exit 1
fi

if [ -z "$OPENROUTER_API_KEY" ]; then
    echo "Error: OPENROUTER_API_KEY is required"
    exit 1
fi

echo "================================================"
echo "  VeloDB RAG Demo with Hybrid Search"
echo "================================================"
echo ""
echo "Configuration:"
echo "  VeloDB Host: $VELODB_HOST"
echo "  VeloDB User: $VELODB_USER"
echo "  VeloDB Database: ${VELODB_DATABASE:-rag_demo}"
echo ""

# Start the backend server in the background
echo "Starting backend server on port 7777..."
cd /app
uv run start &
BACKEND_PID=$!

# Wait for backend to be ready
echo "Waiting for backend to initialize..."
sleep 5

# Start the frontend server (dev mode)
echo "Starting frontend on port 3001..."
cd /app/agent-ui
npm run dev -- -H 0.0.0.0 -p 3001 &
FRONTEND_PID=$!

echo ""
echo "================================================"
echo "  Services Running:"
echo "    Backend API:  http://localhost:7777"
echo "    Chat UI:      http://localhost:3001"
echo "================================================"
echo ""

# Handle shutdown
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT

# Wait for processes
wait
