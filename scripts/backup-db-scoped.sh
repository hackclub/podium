#!/bin/bash
# Scoped backup: dump only the data related to one event (the event row, its
# projects/attendees/votes/referrals/collaborators, and only the users involved
# in any of those) plus the full schema. Other events' data is excluded, though
# users shared with other events are of course still included.
#
# Usage:
#   doppler run --config prd -- ./scripts/backup-db-scoped.sh stasis
#   doppler run --config dev -- ./scripts/backup-db-scoped.sh stasis

set -e
cd "$(dirname "$0")/.."

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}▶${NC} $1"; }
warn()  { echo -e "${YELLOW}▶${NC} $1"; }
error() { echo -e "${RED}▶${NC} $1"; exit 1; }

SLUG="$1"
[[ -z "$SLUG" ]] && error "Usage: $0 <event-slug>"
[[ ! "$SLUG" =~ ^[a-z0-9_-]+$ ]] && error "Event slug must match [a-z0-9_-]+"

[[ -z "$PODIUM_DATABASE_URL" ]] && { echo "PODIUM_DATABASE_URL is not set. Run via: doppler run --config <env> -- $0 $SLUG"; exit 1; }

# Detect container runtime
if command -v docker &>/dev/null; then
  CONTAINER="docker"
elif command -v podman &>/dev/null; then
  CONTAINER="podman"
else
  error "Neither docker nor podman found"
fi

# Use native image for the host architecture to avoid Rosetta/QEMU emulation issues
case "$(uname -m)" in
  arm64|aarch64) PLATFORM="linux/arm64" ;;
  x86_64)        PLATFORM="linux/amd64" ;;
  *)             PLATFORM="linux/$(uname -m)" ;;
esac

# Parse connection params safely (URL via env var, not shell-interpolated into Python source)
eval "$(PARSE_ME="$PODIUM_DATABASE_URL" python3 -c "
import os, shlex
from urllib.parse import urlparse, unquote
url = os.environ['PARSE_ME'].replace('+asyncpg', '')
if '://' not in url:
    url = 'postgresql://' + url
u = urlparse(url)
host = u.hostname or 'localhost'
if host == 'localhost': host = 'host.docker.internal'
for k, v in [('PG_HOST', host), ('PG_PORT', str(u.port or 5432)),
             ('PG_USER', unquote(u.username or '')), ('PG_PASS', unquote(u.password or '')),
             ('PG_DB', u.path.lstrip('/').split('?')[0])]:
    print(k + '=' + shlex.quote(v))
")"

BACKUP_DIR="backups"
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PREFIX="${BACKUP_DIR}/podium_${SLUG}_${TIMESTAMP}"

info "Scoping backup to event '$SLUG' (using $CONTAINER)..."

# 1. Full schema — tables/columns are shared across all events, so the DDL itself
#    isn't event-scoped. Only the data below is filtered. Written straight into
#    the final .sql file; the scoped data below is appended to the same file.
info "Dumping schema..."
$CONTAINER run --rm --platform "$PLATFORM" \
  -e PGPASSWORD="$PG_PASS" -e PGSSLMODE=require \
  postgres:17 pg_dump \
  -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" \
  --schema-only --no-owner --no-privileges \
  > "${PREFIX}.sql"

psql_run() {
  $CONTAINER run --rm --platform "$PLATFORM" \
    -e PGPASSWORD="$PG_PASS" -e PGSSLMODE=require \
    postgres:17 psql \
    -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" \
    -v "ON_ERROR_STOP=1" -t -A -c "$1"
}

# Resolve the event id first (slug was already validated against [a-z0-9_-]+,
# so it's safe to interpolate into a SQL string literal below).
EVENT_ID=$(psql_run "SELECT id FROM events WHERE slug = '$SLUG'")
[[ -z "$EVENT_ID" ]] && error "No event found with slug '$SLUG'"
[[ ! "$EVENT_ID" =~ ^[0-9a-f-]{36}$ ]] && error "Unexpected event id format: $EVENT_ID"

# 2. Scoped data. Loaded in FK-safe order: users -> events -> projects ->
#    event_attendees -> project_collaborators -> votes -> referrals.
# pg_dump's schema section resets search_path to '' (its own CREATE TABLE
# statements are schema-qualified, so that's fine) — our unqualified COPY
# blocks below need it restored to public or "relation does not exist" errors.
info "Dumping scoped data for event $EVENT_ID..."

echo "SET search_path = public;" >> "${PREFIX}.sql"

CSV_DIR="${PREFIX}_csv"
mkdir -p "$CSV_DIR"

dump_table() {
  local table="$1" query="$2"
  echo "COPY ${table} FROM stdin;" >> "${PREFIX}.sql"
  psql_run "COPY (${query}) TO STDOUT;" >> "${PREFIX}.sql"
  echo '\.' >> "${PREFIX}.sql"

  # CSV for inspection — same aligned format as backup-db.sh, valid CSV via csv.writer
  psql_run "COPY (${query}) TO STDOUT WITH CSV HEADER" | python3 -c "
import csv, sys
rows = list(csv.reader(sys.stdin))
if not rows:
    sys.exit(0)
widths = [max(len(str(row[i])) for row in rows) for i in range(len(rows[0]))]
writer = csv.writer(open('${CSV_DIR}/${table}.csv', 'w', newline=''))
for row in rows:
    writer.writerow([str(val).ljust(widths[i]) for i, val in enumerate(row)])
"
}

dump_table users "SELECT * FROM users WHERE id IN (
  SELECT owner_id FROM events WHERE id = '$EVENT_ID'
  UNION SELECT user_id FROM event_attendees WHERE event_id = '$EVENT_ID'
  UNION SELECT owner_id FROM projects WHERE event_id = '$EVENT_ID'
  UNION SELECT pc.user_id FROM project_collaborators pc JOIN projects p ON p.id = pc.project_id WHERE p.event_id = '$EVENT_ID'
  UNION SELECT voter_id FROM votes WHERE event_id = '$EVENT_ID'
  UNION SELECT user_id FROM referrals WHERE event_id = '$EVENT_ID'
)"
dump_table events "SELECT * FROM events WHERE id = '$EVENT_ID'"
dump_table projects "SELECT * FROM projects WHERE event_id = '$EVENT_ID'"
dump_table event_attendees "SELECT * FROM event_attendees WHERE event_id = '$EVENT_ID'"
dump_table project_collaborators "SELECT pc.* FROM project_collaborators pc JOIN projects p ON p.id = pc.project_id WHERE p.event_id = '$EVENT_ID'"
dump_table votes "SELECT * FROM votes WHERE event_id = '$EVENT_ID'"
dump_table referrals "SELECT * FROM referrals WHERE event_id = '$EVENT_ID'"

info "✓ Scoped backup complete:"
echo "  ${PREFIX}.sql ($(du -h "${PREFIX}.sql" | cut -f1)) — schema + scoped data, restorable dump"
echo "  ${CSV_DIR}/ ($(du -sh "${CSV_DIR}" | cut -f1)) — CSVs for inspection"
echo ""
warn "Restore into an EMPTY database with: psql <target-url> -f ${PREFIX}.sql"
