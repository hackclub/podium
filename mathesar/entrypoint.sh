#!/bin/bash
set -e

# Run bootstrap if admin doesn't exist yet
# Uses Python from the Mathesar environment
echo "Checking if bootstrap is needed..."
python /code/bootstrap.py

# Start Mathesar normally
# -n: use system gunicorn
# -s: run Django migrations
# -e: prefer exported env vars
# (no -f: we want it to fail if DB isn't configured)
exec bash ./bin/mathesar run -nse
