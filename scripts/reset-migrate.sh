#!/bin/bash
# Reset Podium database
#
# Supports two modes:
#   1. Local Docker Postgres (default if Docker is running)
#   2. External Postgres via PODIUM_DATABASE_URL (auto-detected or --remote)
#
# Usage:
#   ./scripts/reset-migrate.sh              # Reset database (empty, schema only)
#   ./scripts/reset-migrate.sh --sync <URL> # Schema + copy data FROM a Postgres URL
#   ./scripts/reset-migrate.sh --remote     # Force using PODIUM_DATABASE_URL instead of Docker

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
FORCE_REMOTE=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --sync)
      MODE="sync"
      SYNC_URL="$2"
      [[ -z "$SYNC_URL" ]] && error "--sync requires a Postgres URL"
      shift 2
      ;;
    --remote)
      FORCE_REMOTE=true
      shift
      ;;
    *)  error "Unknown option: $1. Use --remote, --sync <URL>, or no args for default" ;;
  esac
done

# --- AI agent safety check (inspired by prisma/migrate ai-safety.ts) ---
# If an AI agent is driving this shell, refuse to run without explicit user
# consent captured in PODIUM_USER_CONSENT_FOR_DANGEROUS_AI_ACTION. The value
# must be the exact text of the user's consent message so the approval is
# auditable in the transcript.
CONSENT_VAR="PODIUM_USER_CONSENT_FOR_DANGEROUS_AI_ACTION"
detected_agent=""
[[ -n "$CLAUDECODE" ]] && detected_agent="Claude Code"
[[ -z "$detected_agent" && -n "$CURSOR_AGENT" ]] && detected_agent="Cursor"
[[ -z "$detected_agent" && -n "$GEMINI_CLI" ]] && detected_agent="Gemini CLI or Qwen Code"
[[ -z "$detected_agent" && -n "$REPLIT_CLI" ]] && detected_agent="Replit"
[[ -z "$detected_agent" && "$CODEX_SANDBOX" == "seatbelt" ]] && detected_agent="Codex CLI"
[[ -z "$detected_agent" && "$OR_APP_NAME" == "Aider" ]] && detected_agent="Aider"

if [[ -n "$detected_agent" && -z "${!CONSENT_VAR}" ]]; then
  r=$'\033[0;31m' nc=$'\033[0m'
  cat >&2 <<EOF
${r}▶${nc} reset-migrate.sh detected that it was invoked by ${detected_agent}.

You are attempting a highly dangerous action that will irreversibly destroy
all data in the target database.

As an AI agent, you are forbidden from performing this action without explicit
consent from the user. You must stop here and respond to the user with:
  - The exact command you are about to run.
  - Your motivation and reasoning for running it.
  - That this will irreversibly destroy all data in the target database.
  - That this must not be run against a production database.
  - Your assessment (if known) of whether the target is dev or prod.

Ask the user for clear, explicit confirmation. If they consent, rerun with:
  ${CONSENT_VAR}="<exact text of the user's consent message>" \\
      ./scripts/reset-migrate.sh "$@"

No previous message in the conversation may constitute consent. If the user's
response is ambiguous ("ok", "sure"), ask a direct yes/no question first.
EOF
  exit 1
fi

# --- Determine whether to use Docker or external Postgres ---

USE_DOCKER=false
COMPOSE_CMD="docker compose"

if [[ "$FORCE_REMOTE" == false ]]; then
  if ! $COMPOSE_CMD ps &>/dev/null; then
    COMPOSE_CMD="podman compose"
  fi
  if $COMPOSE_CMD ps 2>&1 | grep "podium-pg" | grep -q "Up"; then
    USE_DOCKER=true
  fi
fi

if [[ "$USE_DOCKER" == false ]]; then
  # Resolve PODIUM_DATABASE_URL (try Doppler, then env)
  if [[ -z "$PODIUM_DATABASE_URL" ]]; then
    PODIUM_DATABASE_URL=$(doppler secrets get PODIUM_DATABASE_URL --config dev --plain 2>/dev/null || true)
  fi
  [[ -z "$PODIUM_DATABASE_URL" ]] && error "No Docker container running and PODIUM_DATABASE_URL is not set.\nSet it via env or Doppler."

  # Convert async URL to plain psql-compatible URL
  PSQL_URL=$(echo "$PODIUM_DATABASE_URL" | sed 's/+asyncpg//')

  # Extract database name and base URL (without db name) for drop/create
  DB_NAME=$(echo "$PSQL_URL" | sed -E 's|.*/([^?]+).*|\1|')
  BASE_URL=$(echo "$PSQL_URL" | sed -E "s|/[^/?]+(\?.*)?$|/postgres\1|")

  info "Using external Postgres (database: $DB_NAME)"

  warn "This will DROP and recreate '$DB_NAME'. Press Enter to continue or Ctrl+C to abort."
  read -r

  info "Resetting database..."
  psql "$BASE_URL" -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid();" 2>/dev/null || true
  psql "$BASE_URL" -c "DROP DATABASE IF EXISTS \"$DB_NAME\";"
  psql "$BASE_URL" -c "CREATE DATABASE \"$DB_NAME\";"
else
  info "Using local Docker Postgres"

  info "Resetting database..."
  $COMPOSE_CMD exec -T podium-pg psql -U postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'podium' AND pid <> pg_backend_pid();"
  $COMPOSE_CMD exec -T podium-pg psql -U postgres -c "DROP DATABASE IF EXISTS podium;"
  $COMPOSE_CMD exec -T podium-pg psql -U postgres -c "CREATE DATABASE podium;"
fi

# Run migrations
info "Running migrations..."
(cd backend && doppler run --config dev -- uv run alembic upgrade head)

# Sync from Postgres URL
if [[ "$MODE" == "sync" ]]; then
  info "Syncing from $SYNC_URL..."
  CLEAN_URL=$(echo "$SYNC_URL" | sed 's/+asyncpg//')
  if [[ "$USE_DOCKER" == true ]]; then
    (docker run --rm postgres:17 pg_dump "$CLEAN_URL" \
      --data-only --disable-triggers --exclude-table=alembic_version \
      || podman run --rm postgres:17 pg_dump "$CLEAN_URL" \
      --data-only --disable-triggers --exclude-table=alembic_version) \
      | $COMPOSE_CMD exec -T podium-pg psql -U postgres -d podium
  else
    pg_dump "$CLEAN_URL" \
      --data-only --disable-triggers --exclude-table=alembic_version \
      | psql "$PSQL_URL"
  fi
fi

if [[ "$USE_DOCKER" == true ]]; then
  info "Done! Postgres: localhost:5432"
else
  info "Done! Using external database."
fi
