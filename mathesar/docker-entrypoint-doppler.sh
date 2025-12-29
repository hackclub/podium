#!/bin/sh
set -e

# If DOPPLER_TOKEN is set, use Doppler to inject secrets
# Otherwise, assume secrets are passed directly via environment
if [ -n "$DOPPLER_TOKEN" ]; then
  echo "Fetching secrets from Doppler..."
  # Map MATHESAR_DB_PASSWORD -> POSTGRES_PASSWORD (Doppler uses our naming, Postgres needs its naming)
  exec doppler run -- sh -c 'export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-$MATHESAR_DB_PASSWORD}"; exec /usr/local/bin/docker-entrypoint.sh "$@"' -- "$@"
else
  echo "DOPPLER_TOKEN not set, using environment variables directly"
  exec /usr/local/bin/docker-entrypoint.sh "$@"
fi
