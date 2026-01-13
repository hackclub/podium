# NocoDB Admin

[NocoDB](https://nocodb.com/) provides a spreadsheet-like UI for managing PostgreSQL data.

## Local Setup

NocoDB is included in `docker-compose.yaml`:

```bash
docker compose up -d
# Open http://localhost:8080
```

First time:
1. Create admin account
2. Create a new base → Connect to external database
3. Connection: `postgresql://postgres:localpass@postgres:5432/podium`

## Production

Deploy NocoDB as a separate service pointing to production Postgres. See [NocoDB docs](https://docs.nocodb.com/) for options.

## Tips

- NocoDB stores its own metadata separately from your app data
- Create filtered views for common queries (e.g., "Active Events")
- Use Gallery or Grid views for different browsing needs
