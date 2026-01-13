#!/bin/bash
set -e
cd /code

# Save env vars that should override Doppler (set by docker-compose)
export _OVERRIDE_PODIUM_URL="$PODIUM_DATABASE_URL"

run_mathesar() {
  # Restore override if it was set (takes precedence over Doppler)
  if [ -n "$_OVERRIDE_PODIUM_URL" ]; then
    export PODIUM_DATABASE_URL="$_OVERRIDE_PODIUM_URL"
  fi

  # Map MATHESAR_DB_PASSWORD -> POSTGRES_PASSWORD
  export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-$MATHESAR_DB_PASSWORD}"

  echo "PODIUM_DATABASE_URL=$PODIUM_DATABASE_URL"

  echo "Running Mathesar setup..."
  python -m mathesar.install

  echo "Running bootstrap..."
  python /code/bootstrap.py

  echo "Starting Mathesar..."
  exec gunicorn config.wsgi -b 0.0.0.0:8000
}

if [ -n "$DOPPLER_TOKEN" ]; then
  echo "Fetching secrets from Doppler..."
  # Export function so it's available in doppler run subshell
  export -f run_mathesar
  exec doppler run -- bash -c 'run_mathesar'
else
  echo "Using environment variables directly"
  run_mathesar
fi
