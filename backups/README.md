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
doppler run --config dev -- ./scripts/restore-db.sh            # latest .dump
doppler run --config prd -- ./scripts/restore-db.sh backups/podium_20260421_120000.dump  # specific file
```
