#!/bin/bash
# Backup Podium database to multiple formats
#
# Usage:
#   ./scripts/backup-db.sh              # Backup dev database
#   ./scripts/backup-db.sh --config prd # Backup production database

set -e
cd "$(dirname "$0")/.."

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info() { echo -e "${GREEN}▶${NC} $1"; }
warn() { echo -e "${YELLOW}▶${NC} $1"; }

# Parse config argument
CONFIG="dev"
if [[ "$1" == "--config" ]]; then
  CONFIG="$2"
  shift 2
fi

# Get database URL
DB_URL=$(doppler secrets get PODIUM_DATABASE_URL --config "$CONFIG" --plain 2>/dev/null)
[[ -z "$DB_URL" ]] && { echo "Failed to get PODIUM_DATABASE_URL from Doppler config '$CONFIG'"; exit 1; }

# Convert async URL to psql-compatible and fix localhost for Docker
PSQL_URL=$(echo "$DB_URL" | sed 's/+asyncpg//' | sed 's/@localhost/@host.docker.internal/g')

# Create backup directory
BACKUP_DIR="backups"
mkdir -p "$BACKUP_DIR"

# Timestamp for filenames
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PREFIX="${BACKUP_DIR}/podium_${CONFIG}_${TIMESTAMP}"

info "Backing up database (config: $CONFIG)..."

# 1. Full database dump (custom format - compressed, restorable)
info "Creating full dump..."
docker run --rm postgres:17 pg_dump "$PSQL_URL" \
  --format=custom --compress=9 \
  > "${PREFIX}.dump" 2>/dev/null || \
podman run --rm postgres:17 pg_dump "$PSQL_URL" \
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
  docker run --rm postgres:17 psql "$PSQL_URL" -c "\COPY $table TO STDOUT WITH (FORMAT CSV, HEADER true)" \
    > "$TMP_CSV" 2>/dev/null || \
  podman run --rm postgres:17 psql "$PSQL_URL" -c "\COPY $table TO STDOUT WITH (FORMAT CSV, HEADER true)" \
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
