# Database Backups

## Create Backup

```bash
doppler run --config dev -- ./scripts/backup-db.sh
doppler run --config prd -- ./scripts/backup-db.sh
```

Creates:
- `*.dump` — Full backup (use to restore)
- `*_csv/` — Each table as CSV (use to inspect data)

## Restore

```bash
# Full restore from latest .dump
docker run --rm -i postgres:17 pg_restore \
  -d "$(doppler secrets get PODIUM_DATABASE_URL --config dev --plain | sed 's/+asyncpg//' | sed 's/@localhost/@host.docker.internal/')" \
  --clean --if-exists \
  < $(ls -t backups/*.dump | head -1)
```
