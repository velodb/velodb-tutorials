#!/bin/bash
#
# VeloDB Integration Lab - Quick Start Script
#
# This script helps you quickly set up and run the lab environment.
# All CDC sync happens automatically via Docker Compose.
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "================================================"
echo "  VeloDB Real-Time Data Integration Lab"
echo "================================================"
echo -e "${NC}"

# Check prerequisites
check_prerequisites() {
    echo -e "${YELLOW}Checking prerequisites...${NC}"

    # Check Docker
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Error: Docker is not installed${NC}"
        exit 1
    fi
    echo -e "  ${GREEN}✓${NC} Docker installed"

    # Check Docker Compose
    if ! docker compose version &> /dev/null; then
        echo -e "${RED}Error: Docker Compose is not installed${NC}"
        exit 1
    fi
    echo -e "  ${GREEN}✓${NC} Docker Compose installed"

    # Check if Docker is running
    if ! docker info &> /dev/null; then
        echo -e "${RED}Error: Docker is not running${NC}"
        exit 1
    fi
    echo -e "  ${GREEN}✓${NC} Docker is running"

    echo ""
}

# Setup environment file
setup_env() {
    if [ ! -f ".env" ]; then
        echo -e "${YELLOW}Setting up environment...${NC}"

        if [ -f ".env.example" ]; then
            cp .env.example .env
            echo -e "  ${GREEN}✓${NC} Created .env from .env.example"
            echo ""
            echo -e "${YELLOW}IMPORTANT: Please edit .env file with your VeloDB Cloud credentials:${NC}"
            echo "  - VELODB_FE_HOST (your cluster hostname)"
            echo "  - VELODB_PASSWORD (your password)"
            echo ""
            echo "You can find these in VeloDB Cloud Console > Cluster > Connection Info"
            echo ""
            read -p "Press Enter after configuring .env to continue..."
        else
            echo -e "${RED}Error: .env.example not found${NC}"
            exit 1
        fi
    else
        echo -e "  ${GREEN}✓${NC} .env file exists"
    fi
}

# Create VeloDB schema reminder
velodb_schema_reminder() {
    echo ""
    echo -e "${YELLOW}VeloDB Schema Setup:${NC}"
    echo "Before starting, ensure you've created the target tables in VeloDB:"
    echo ""
    echo "  1. Open VeloDB Cloud Console > SQL Editor"
    echo "  2. Run the SQL from: flink/velodb_schema.sql"
    echo ""
    read -p "Press Enter after creating VeloDB tables to continue..."
}

# Start services
start_services() {
    echo -e "${YELLOW}Starting Docker services...${NC}"
    docker compose up -d --build

    echo ""
    echo -e "${YELLOW}Waiting for services to initialize...${NC}"

    # Wait for PostgreSQL
    echo -n "  Waiting for PostgreSQL..."
    until docker exec postgres pg_isready -U labuser -d user_analytics > /dev/null 2>&1; do
        echo -n "."
        sleep 2
    done
    echo -e " ${GREEN}✓${NC}"

    # Wait for Flink
    echo -n "  Waiting for Flink CDC..."
    sleep 15
    until curl -s http://localhost:8081/jobs/overview > /dev/null 2>&1; do
        echo -n "."
        sleep 5
    done
    echo -e " ${GREEN}✓${NC}"

    # Check Flink jobs
    echo ""
    echo -e "${YELLOW}Flink CDC Job Status:${NC}"
    curl -s http://localhost:8081/jobs/overview 2>&1 | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for job in data.get('jobs', []):
        name = job['name'].replace('insert-into_default_catalog.default_database.', '')
        print(f\"  {job['state']:10} {name}\")
except:
    print('  Waiting for jobs to start...')
" 2>/dev/null || echo "  Jobs starting..."

    echo ""
    echo -e "${YELLOW}Service Status:${NC}"
    docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
}

# Display next steps
show_next_steps() {
    echo ""
    echo -e "${GREEN}================================================"
    echo "  Lab Environment Ready!"
    echo "================================================${NC}"
    echo ""
    echo "Access Points:"
    echo "  • Flink Web UI:  http://localhost:8081"
    echo "  • Superset:      http://localhost:8088 (admin/admin)"
    echo "  • PostgreSQL:    localhost:5432 (labuser/labpass)"
    echo ""
    echo "Data Flow:"
    echo "  Datagen → PostgreSQL → Flink CDC → VeloDB Cloud → Superset"
    echo ""
    echo "Verify data sync:"
    echo "  docker logs flink-cdc | grep 'Status.*Success'"
    echo ""
    echo "Read the full tutorial:"
    echo "  less TUTORIAL.md"
    echo ""
    echo -e "${BLUE}Happy learning!${NC}"
}

# Stop services
stop_services() {
    echo -e "${YELLOW}Stopping Docker services...${NC}"
    docker compose down
    echo -e "${GREEN}Services stopped.${NC}"
}

# Show logs
show_logs() {
    local service="${1:-}"
    if [ -n "$service" ]; then
        docker compose logs -f "$service"
    else
        docker compose logs -f
    fi
}

# Check status
check_status() {
    echo -e "${YELLOW}Service Status:${NC}"
    docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

    echo ""
    echo -e "${YELLOW}Flink CDC Jobs:${NC}"
    curl -s http://localhost:8081/jobs/overview 2>&1 | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for job in data.get('jobs', []):
        name = job['name'].replace('insert-into_default_catalog.default_database.', '')
        print(f\"  {job['state']:10} {name}\")
except Exception as e:
    print(f'  Error: {e}')
" 2>/dev/null || echo "  Flink not ready"
}

# Main menu
main() {
    case "${1:-start}" in
        start)
            check_prerequisites
            setup_env
            velodb_schema_reminder
            start_services
            show_next_steps
            ;;
        stop)
            stop_services
            ;;
        restart)
            stop_services
            sleep 2
            start_services
            show_next_steps
            ;;
        status)
            check_status
            ;;
        logs)
            show_logs "${2:-}"
            ;;
        *)
            echo "Usage: $0 {start|stop|restart|status|logs [service]}"
            echo ""
            echo "Commands:"
            echo "  start   - Start all lab services (PostgreSQL, Flink CDC, Datagen, Superset)"
            echo "  stop    - Stop all lab services"
            echo "  restart - Restart all lab services"
            echo "  status  - Show service and Flink job status"
            echo "  logs    - Show service logs (optionally specify service name)"
            echo ""
            echo "Services: postgres, flink-cdc, datagen, superset"
            exit 1
            ;;
    esac
}

main "$@"
