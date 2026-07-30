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

## Scoped Backup (single event)

Dump just one event's data — the event, its projects/votes/referrals/attendees/collaborators,
and only the users involved — instead of the whole DB:

```bash
doppler run --config prd -- ./scripts/backup-db-scoped.sh <event-slug>
```

Creates:
- `*.sql` — schema + scoped data, plain SQL (not a `pg_dump` custom-format `.dump` —
  `pg_dump` has no row-level `--where` filter, so this can't be restored with `restore-db.sh`/`pg_restore`)
- `*_csv/` — same as above, for inspection

Restore into an **empty** database (it runs `CREATE TABLE`, so the target must not already have the schema):

```bash
psql <target-database-url> -f backups/podium_stasis_20260730_143216.sql
```
