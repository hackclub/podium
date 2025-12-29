#!/bin/bash
set -e
cd /code

# If DOPPLER_TOKEN is set, fetch secrets from Doppler
# Otherwise, assume secrets are passed directly via environment
if [ -n "$DOPPLER_TOKEN" ]; then
  echo "Fetching secrets from Doppler..."
  exec doppler run -- bash -c '
    cd /code
    # Map MATHESAR_DB_PASSWORD -> POSTGRES_PASSWORD
    export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-$MATHESAR_DB_PASSWORD}"
    
    # Run migrations first (Mathesar needs tables before bootstrap can check users)
    echo "Running Mathesar setup (migrations)..."
    python -m mathesar.install
    
    # Now run bootstrap to create admin user and Podium connection
    echo "Running bootstrap..."
    python /code/bootstrap.py
    
    # Start Mathesar with gunicorn
    echo "Starting Mathesar..."
    exec gunicorn config.wsgi -b 0.0.0.0:8000
  '
else
  echo "DOPPLER_TOKEN not set, using environment variables directly"
  
  # Run migrations first
  echo "Running Mathesar setup (migrations)..."
  python -m mathesar.install
  
  # Now run bootstrap
  echo "Running bootstrap..."
  python /code/bootstrap.py
  
  # Start Mathesar with gunicorn
  echo "Starting Mathesar..."
  exec gunicorn config.wsgi -b 0.0.0.0:8000
fi
