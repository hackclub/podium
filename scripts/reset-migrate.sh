#!/bin/bash
# Reset local Podium database and/or migrate data from Airtable
#
# Usage:
#   ./scripts/reset-migrate.sh                        # Empty local database with schema only
#   ./scripts/reset-migrate.sh --sync <URL>           # Schema + copy data from Postgres URL
#   ./scripts/reset-migrate.sh --migrate-dev          # Schema + migrate from Airtable dev
#   ./scripts/reset-migrate.sh --checkout-prod        # Schema + migrate from Airtable prod -> local DB
#   ./scripts/reset-migrate.sh --migrate-prod         # Migrate Airtable prod -> prod Postgres (no local reset)

set -e
cd "$(dirname "$0")/.."

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info() { echo -e "${GREEN}▶${NC} $1"; }
warn() { echo -e "${YELLOW}▶${NC} $1"; }
error() { echo -e "${RED}▶${NC} $1"; exit 1; }

MODE=""
SYNC_URL=""

case "$1" in
  --sync)
    MODE="sync"
    SYNC_URL="$2"
    [[ -z "$SYNC_URL" ]] && error "--sync requires a Postgres URL"
    ;;
  --migrate-dev)    MODE="migrate-dev" ;;
  --checkout-prod)  MODE="checkout-prod" ;;
  --migrate-prod)   MODE="migrate-prod" ;;
  "")               MODE="reset" ;;
  *)                error "Unknown option: $1. Use --sync <URL>, --migrate-dev, --checkout-prod, or --migrate-prod" ;;
esac

# --migrate-prod doesn't need local Docker, skip verification
if [[ "$MODE" != "migrate-prod" ]]; then
  # Verify Docker is running
  docker compose ps --quiet podium-pg >/dev/null 2>&1 || error "Run 'docker compose up -d podium-pg' first"

  # Reset database
  info "Resetting database..."
  docker compose exec -T podium-pg psql -U postgres -c "DROP DATABASE IF EXISTS podium;" 2>/dev/null || true
  docker compose exec -T podium-pg psql -U postgres -c "CREATE DATABASE podium;"

  # Run migrations
  info "Running migrations..."
  (cd backend && doppler run --config dev -- uv run alembic upgrade head)
fi

# Sync from Postgres URL
if [[ "$MODE" == "sync" ]]; then
  info "Syncing from $SYNC_URL..."
  # Strip asyncpg driver if present
  CLEAN_URL=$(echo "$SYNC_URL" | sed 's/+asyncpg//')
  docker run --rm postgres:17 pg_dump "$CLEAN_URL" \
    --data-only --disable-triggers --exclude-table=alembic_version \
    | docker compose exec -T podium-pg psql -U postgres -d podium
fi

# Migrate from Airtable dev
if [[ "$MODE" == "migrate-dev" ]]; then
  info "Migrating from Airtable dev..."
  (cd backend && doppler run --config dev -- uv run python scripts/migrate_from_airtable.py)
fi

# Checkout prod Airtable -> local DB
if [[ "$MODE" == "checkout-prod" ]]; then
  warn "⚠️  You are about to migrate PRODUCTION Airtable data to your local database."
  echo -n "Are you sure? (y/N) "
  read -r confirm
  [[ "$confirm" != "y" && "$confirm" != "Y" ]] && error "Aborted."
  
  info "Migrating from Airtable prod -> local DB..."
  # Fetch prod Airtable token, use dev config for everything else, override Airtable IDs from settings.toml [default]
  export PROD_AIRTABLE_TOKEN=$(doppler secrets get PODIUM_AIRTABLE_TOKEN --config prd --plain)
  (
    cd backend
    # Export dev secrets (for local DB URL)
    set -a
    eval "$(doppler secrets download --config dev --no-file --format env-no-quotes)"
    set +a
    # Override with prod Airtable IDs from settings.toml [default] section
    eval "$(uv run python -c "
import tomllib
with open('settings.toml', 'rb') as f:
    cfg = tomllib.load(f)['default']
for k, v in cfg.items():
    if k.startswith('airtable_'):
        print(f'export PODIUM_{k.upper()}=\"{v}\"')
")"
    export PODIUM_AIRTABLE_TOKEN="$PROD_AIRTABLE_TOKEN"
    uv run python scripts/migrate_from_airtable.py
  )
fi

# Migrate prod Airtable -> prod Postgres
if [[ "$MODE" == "migrate-prod" ]]; then
  warn "⚠️  You are about to migrate PRODUCTION Airtable data to PRODUCTION PostgreSQL."
  warn "⚠️  This will modify the production database!"
  echo -n "Type 'yes' to confirm: "
  read -r confirm
  [[ "$confirm" != "yes" ]] && error "Aborted. You must type 'yes' to confirm."
  
  info "Running migrations on prod Postgres..."
  (cd backend && doppler run --config prd -- uv run alembic upgrade head)

  info "Migrating from Airtable prod -> prod Postgres..."
  (
    cd backend
    # Export prd secrets
    set -a
    eval "$(doppler secrets download --config prd --no-file --format env-no-quotes)"
    set +a
    # Override with prod Airtable IDs from settings.toml [default] section
    eval "$(uv run python -c "
import tomllib
with open('settings.toml', 'rb') as f:
    cfg = tomllib.load(f)['default']
for k, v in cfg.items():
    if k.startswith('airtable_'):
        print(f'export PODIUM_{k.upper()}=\"{v}\"')
")"
    uv run python scripts/migrate_from_airtable.py
  )
fi

# Restart Mathesar if running
if docker compose ps --quiet mathesar >/dev/null 2>&1; then
  info "Restarting Mathesar..."
  docker compose restart mathesar >/dev/null 2>&1 || true
fi

info "Done! Postgres: localhost:5432 | Mathesar: http://localhost:8000"
