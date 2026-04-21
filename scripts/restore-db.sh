#!/bin/bash
# Restore Podium database from a .dump file
#
# Usage:
#   doppler run --config dev -- ./scripts/restore-db.sh
#   doppler run --config prd -- ./scripts/restore-db.sh
#   doppler run --config dev -- ./scripts/restore-db.sh backups/podium_20260421_120000.dump

set -e
cd "$(dirname "$0")/.."

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}▶${NC} $1"; }
error() { echo -e "${RED}▶${NC} $1"; exit 1; }

DUMP_FILE="${1:-$(ls -t backups/*.dump 2>/dev/null | head -1)}"
[[ -z "$DUMP_FILE" ]]          && error "No .dump file found in backups/"
[[ ! -f "$DUMP_FILE" ]]        && error "File not found: $DUMP_FILE"
[[ -z "$PODIUM_DATABASE_URL" ]] && error "PODIUM_DATABASE_URL is not set. Run via: doppler run --config <env> -- $0"

# Detect container runtime
if command -v docker &>/dev/null; then
  CONTAINER="docker"
elif command -v podman &>/dev/null; then
  CONTAINER="podman"
else
  error "Neither docker nor podman found"
fi

# Use native image for the host architecture
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

info "Restoring $DUMP_FILE → $PG_HOST:$PG_PORT/$PG_DB"
info "This will DROP and recreate all objects. Press Enter to continue or Ctrl+C to abort."
read -r

$CONTAINER run --rm -i --platform "$PLATFORM" \
  -e PGPASSWORD="$PG_PASS" -e PGSSLMODE=require \
  postgres:17 pg_restore \
  -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" \
  --clean --if-exists --no-owner --no-acl \
  < "$DUMP_FILE"

info "✓ Restore complete"
