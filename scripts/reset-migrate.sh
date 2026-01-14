#!/bin/bash
# Reset LOCAL Podium database (cannot affect production)
#
# This script only touches the local Docker Postgres container.
# It uses `docker compose exec` and `doppler --config dev`.
#
# Usage:
#   ./scripts/reset-migrate.sh              # Empty local database with schema only
#   ./scripts/reset-migrate.sh --sync <URL> # Schema + copy data FROM a Postgres URL
#
# For Airtable migrations, see docs/migrations/airtable-to-postgres.md

set -e
cd "$(dirname "$0")/.."

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info() { echo -e "${GREEN}▶${NC} $1"; }
warn() { echo -e "${YELLOW}▶${NC} $1"; }
error() { echo -e "${RED}▶${NC} $1"; exit 1; }

MODE="reset"
SYNC_URL=""

case "$1" in
  --sync)
    MODE="sync"
    SYNC_URL="$2"
    [[ -z "$SYNC_URL" ]] && error "--sync requires a Postgres URL"
    ;;
  "") MODE="reset" ;;
  *)  error "Unknown option: $1. Use --sync <URL> or see docs/migrations/ for Airtable" ;;
esac

# Verify Docker is running
docker compose ps --quiet podium-pg >/dev/null 2>&1 || error "Run 'docker compose up -d' first"

# Reset database
info "Resetting database..."
docker compose exec -T podium-pg psql -U postgres -c "DROP DATABASE IF EXISTS podium;" 2>/dev/null || true
docker compose exec -T podium-pg psql -U postgres -c "CREATE DATABASE podium;"

# Run migrations
info "Running migrations..."
(cd backend && doppler run --config dev -- uv run alembic upgrade head)

# Sync from Postgres URL
if [[ "$MODE" == "sync" ]]; then
  info "Syncing from $SYNC_URL..."
  CLEAN_URL=$(echo "$SYNC_URL" | sed 's/+asyncpg//')
  docker run --rm postgres:17 pg_dump "$CLEAN_URL" \
    --data-only --disable-triggers --exclude-table=alembic_version \
    | docker compose exec -T podium-pg psql -U postgres -d podium
fi

info "Done! Postgres: localhost:5432"
