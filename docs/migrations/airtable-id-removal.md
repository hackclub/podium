# Remove `airtable_id` Fields

**Status:** Delete after production migration is verified stable.

The `airtable_id` fields were added temporarily for cross-referencing during Airtable→Postgres migration.

## Steps

### 1. Remove from models

Delete the `airtable_id` field from each model in `backend/podium/db/postgres/`:
- `user.py`
- `event.py`
- `project.py`
- `vote.py`
- `referral.py`

### 2. Generate migration

```bash
cd backend && doppler run --config dev -- uv run alembic revision --autogenerate -m "remove_airtable_id_fields"
```

Review the generated file to confirm it drops columns and indexes.

### 3. Apply

```bash
# Local
cd backend && doppler run --config dev -- uv run alembic upgrade head

# Production
cd backend && doppler run --config prd -- uv run alembic upgrade head
```

### 4. Cleanup

- Delete `backend/scripts/migrate_from_airtable.py`
- Remove PyAirtable: `cd backend && uv remove pyairtable`
- Delete this doc and its entry in `migrations/README.md`

## Rollback

```bash
doppler run --config dev -- uv run alembic downgrade -1
```
