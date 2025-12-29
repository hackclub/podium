#!/bin/sh
set -e

if [ -z "$DOPPLER_TOKEN" ]; then
  echo "Error: DOPPLER_TOKEN is not set. Cannot fetch secrets from Doppler." >&2
  exit 1
fi

# Run Doppler to inject secrets (e.g., POSTGRES_PASSWORD),
# then delegate to the official Postgres entrypoint
exec doppler run -- /usr/local/bin/docker-entrypoint.sh "$@"
