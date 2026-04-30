#!/bin/bash
# Database migration script for Neon PostgreSQL

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Neon PostgreSQL Migration Script ===${NC}"

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}Error: DATABASE_URL environment variable not set${NC}"
    exit 1
fi

# Check if alembic is installed
if ! command -v alembic &> /dev/null; then
    echo -e "${YELLOW}Alembic not found. Installing...${NC}"
    pip install alembic
fi

# Initialize alembic if not already initialized
if [ ! -d "alembic" ]; then
    echo -e "${YELLOW}Initializing Alembic...${NC}"
    alembic init alembic

    # Update alembic.ini with DATABASE_URL
    sed -i "s|sqlalchemy.url = .*|sqlalchemy.url = ${DATABASE_URL}|g" alembic.ini

    echo -e "${GREEN}Alembic initialized${NC}"
fi

# Function to create migration
create_migration() {
    local message=$1
    echo -e "${YELLOW}Creating migration: ${message}${NC}"
    alembic revision --autogenerate -m "$message"
    echo -e "${GREEN}Migration created${NC}"
}

# Function to apply migrations
apply_migrations() {
    echo -e "${YELLOW}Applying migrations...${NC}"
    alembic upgrade head
    echo -e "${GREEN}Migrations applied successfully${NC}"
}

# Function to rollback migration
rollback_migration() {
    local steps=${1:-1}
    echo -e "${YELLOW}Rolling back ${steps} migration(s)...${NC}"
    alembic downgrade -${steps}
    echo -e "${GREEN}Rollback completed${NC}"
}

# Function to show migration history
show_history() {
    echo -e "${YELLOW}Migration history:${NC}"
    alembic history
}

# Function to check current version
check_version() {
    echo -e "${YELLOW}Current database version:${NC}"
    alembic current
}

# Main menu
case "${1:-}" in
    create)
        if [ -z "$2" ]; then
            echo -e "${RED}Error: Migration message required${NC}"
            echo "Usage: $0 create \"migration message\""
            exit 1
        fi
        create_migration "$2"
        ;;
    apply|upgrade)
        apply_migrations
        ;;
    rollback|downgrade)
        rollback_migration "${2:-1}"
        ;;
    history)
        show_history
        ;;
    current|version)
        check_version
        ;;
    *)
        echo "Usage: $0 {create|apply|rollback|history|current} [args]"
        echo ""
        echo "Commands:"
        echo "  create \"message\"  - Create a new migration"
        echo "  apply             - Apply all pending migrations"
        echo "  rollback [n]      - Rollback n migrations (default: 1)"
        echo "  history           - Show migration history"
        echo "  current           - Show current database version"
        exit 1
        ;;
esac
