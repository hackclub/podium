# Airtable → PostgreSQL Migration

**Status:** Delete after production migration verified stable.

The migration script is idempotent — uses `airtable_id` to skip already-migrated records.

## Local

```bash
# Dev Airtable → local DB
cd backend && doppler run --config dev -- uv run python scripts/migrate_from_airtable.py
```

## Production (Cutover)

### 1. Get prod connection string

```bash
doppler secrets get PODIUM_DATABASE_URL --config prd --plain
```

### 2. Connect via Beekeeper Studio

Open Beekeeper Studio → New Connection → Paste the connection URL (strip `+asyncpg` if present).

### 3. Run Alembic migrations

```bash
cd backend && doppler run --config prd -- uv run alembic upgrade head
```

### 4. (Optional) Truncate if starting fresh

In Beekeeper, run:
```sql
TRUNCATE users, events, projects, votes, referrals, 
         event_attendees, project_collaborators 
RESTART IDENTITY CASCADE;
```

### 5. Run migration

```bash
cd backend && doppler run --config prd -- uv run python scripts/migrate_from_airtable.py
```

### 6. Verify counts

In Beekeeper:
```sql
SELECT 'users', COUNT(*) FROM users
UNION ALL SELECT 'events', COUNT(*) FROM events
UNION ALL SELECT 'projects', COUNT(*) FROM projects;
```

Compare with script output.

## Cleanup

After verified stable — see [airtable-id-removal.md](airtable-id-removal.md).
