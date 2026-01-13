# Mathesar (Local Development Only)

This directory contains Docker configuration for running Mathesar locally as a database admin UI.

**Not for production use.** We use NocoDB for production admin access.

## Usage

```bash
docker compose -f mathesar-local-dev/docker-compose.yaml up -d
# Open http://localhost:8000
```

See `bootstrap.py` for auto-setup of admin user and database connection.
