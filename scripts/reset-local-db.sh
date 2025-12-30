#!/bin/bash
# Reset local Podium database and optionally sync production data
#
# Usage:
#   ./scripts/reset-local-db.sh           # Empty database with schema only
#   ./scripts/reset-local-db.sh --sync    # Schema + copy of production data

set -e
cd "$(dirname "$0")/.."

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info() { echo -e "${GREEN}▶${NC} $1"; }
warn() { echo -e "${YELLOW}▶${NC} $1"; }
error() { echo -e "${RED}▶${NC} $1"; exit 1; }

SYNC_FROM_PROD=false
[[ "$1" == "--sync" ]] && SYNC_FROM_PROD=true

# Verify Docker is running
docker compose ps --quiet podium-pg >/dev/null 2>&1 || error "Run 'docker compose up -d' first"

# Reset database
info "Resetting database..."
docker compose exec -T podium-pg psql -U postgres -c "DROP DATABASE IF EXISTS podium;" 2>/dev/null || true
docker compose exec -T podium-pg psql -U postgres -c "CREATE DATABASE podium;"

# Run migrations (always uses dev config)
info "Running migrations..."
(cd backend && doppler run --config dev -- uv run alembic upgrade head)

# Sync production data if requested
if [[ "$SYNC_FROM_PROD" == true ]]; then
  warn "Syncing from production..."
  PRD_URL=$(doppler secrets get PODIUM_DATABASE_URL --config prd --plain | sed 's/+asyncpg//')
  [[ -z "$PRD_URL" ]] && error "Could not get production URL from Doppler"
  
  # Use postgres container for pg_dump (no local install needed)
  docker run --rm postgres:17 pg_dump "$PRD_URL" \
    --data-only --disable-triggers --exclude-table=alembic_version \
    | docker compose exec -T podium-pg psql -U postgres -d podium
fi

# Restart Mathesar to pick up changes
info "Restarting Mathesar..."
docker compose restart mathesar >/dev/null

info "Done! Postgres: localhost:5432 | Mathesar: http://localhost:8000"
