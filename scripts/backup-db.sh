#!/bin/bash
# Backup Podium database to multiple formats
#
# Usage:
#   doppler run --config dev -- ./scripts/backup-db.sh
#   doppler run --config prd -- ./scripts/backup-db.sh

set -e
cd "$(dirname "$0")/.."

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info() { echo -e "${GREEN}▶${NC} $1"; }
warn() { echo -e "${YELLOW}▶${NC} $1"; }

# Get database URL from environment
[[ -z "$PODIUM_DATABASE_URL" ]] && { echo "PODIUM_DATABASE_URL is not set. Run via: doppler run --config <env> -- $0"; exit 1; }

# Detect container runtime
if command -v docker &>/dev/null; then
  CONTAINER="docker"
elif command -v podman &>/dev/null; then
  CONTAINER="podman"
else
  echo "Neither docker nor podman found"; exit 1
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

# Create backup directory
BACKUP_DIR="backups"
mkdir -p "$BACKUP_DIR"

# Timestamp for filenames
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PREFIX="${BACKUP_DIR}/podium_${TIMESTAMP}"

info "Backing up database (using $CONTAINER)..."

# 1. Full database dump (custom format - compressed, restorable)
info "Creating full dump..."
$CONTAINER run --rm --platform "$PLATFORM" \
  -e PGPASSWORD="$PG_PASS" -e PGSSLMODE=require \
  postgres:17 pg_dump \
  -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" \
  --format=custom --compress=9 \
  > "${PREFIX}.dump"

# 2. Export all tables to CSV (aligned for readability)
info "Exporting to CSV..."
CSV_DIR="${PREFIX}_csv"
mkdir -p "$CSV_DIR"

TABLES=("users" "events" "projects" "votes" "referrals" "event_attendees" "project_collaborators")

for table in "${TABLES[@]}"; do
  TMP_CSV="${CSV_DIR}/${table}.csv.tmp"
  
  # Export raw CSV
  $CONTAINER run --rm --platform "$PLATFORM" \
    -e PGPASSWORD="$PG_PASS" -e PGSSLMODE=require \
    postgres:17 psql \
    -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" \
    -c "\COPY $table TO STDOUT WITH (FORMAT CSV, HEADER true)" \
    > "$TMP_CSV"
  
  # Align columns with spaces for readability
  python3 -c "
import csv
import sys

# Read CSV and calculate column widths
with open('$TMP_CSV', 'r') as f:
    reader = csv.reader(f)
    rows = list(reader)
    
if not rows:
    sys.exit(0)

widths = [max(len(str(row[i])) for row in rows) for i in range(len(rows[0]))]

# Write aligned CSV
with open('${CSV_DIR}/${table}.csv', 'w') as f:
    for row in rows:
        aligned = ', '.join(str(val).ljust(widths[i]) for i, val in enumerate(row))
        f.write(aligned + '\n')
"
  rm "$TMP_CSV"
done

info "✓ Backup complete:"
echo "  ${PREFIX}.dump ($(du -h "${PREFIX}.dump" | cut -f1))"
echo "  ${CSV_DIR}/ ($(du -sh "${CSV_DIR}" | cut -f1))"
echo ""
warn "See backups/README.md for restoration instructions"
