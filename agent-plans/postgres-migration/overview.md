# PostgreSQL Migration Overview (Podium v2)

**Status:** In Progress  
**Last Updated:** 2025-12-29

---

## What We're Doing

**Clean break** from Airtable → PostgreSQL. No feature flags, no dual backends.

| v1 (Current) | v2 (Target) |
|--------------|-------------|
| Airtable (5 req/sec limit) | PostgreSQL |
| Redis cache (workaround) | No cache needed |
| PyAirtable + Pydantic | SQLModel ORM |

---

## Progress

| Phase | Status |
|-------|--------|
| 1. Schema & Infrastructure | ✅ Complete |
| 2. Backfill Script | ✅ Complete (tested locally) |
| 3. Refactor Routers | ✅ Complete |
| 3.5 Code Quality Cleanup | ✅ Complete |
| 3.6 E2E Tests | ✅ Complete |
| 4. Dry-run on Prod Airtable | 🔲 Not started |
| 5. Cutover | 🔲 Not started |
| 6. Cleanup | 🔲 Not started |

---

## Phase 1: Schema & Infrastructure ✅

- [x] SQLModel models in `db/postgres/` (user, event, project, vote, referral, links)
- [x] Models include `airtable_id` for backfill mapping
- [x] Explicit M2M link tables (SQLModel requires these)
- [x] Alembic migrations configured and simplified
- [x] Initial migration generated and applied
- [x] Production Postgres on Coolify with S3 backups
- [ ] ~~GitHub Actions CI~~ (deprioritized)

---

## Phase 2: Backfill Script ✅

**Status:** Complete - tested locally with Airtable data snapshot.

**Migration results (local dev):**
- 3365 users
- 217 events
- 767 projects
- 1266 referrals
- 4078 attendee links
- All M2M relationships preserved

**Run:**
```bash
doppler run --config dev -- python scripts/migrate_from_airtable.py
```

**Note:** This was tested with a snapshot of Airtable data. Production Airtable may have more recent data that hasn't been tested yet.

---

## Phase 3: Refactor Routers ✅

Replaced all Airtable/cache calls with SQLModel async queries.

**Completed:**
- [x] `routers/auth.py` - JWT auth with Postgres user lookup
- [x] `routers/users.py` - CRUD operations with SQLModel
- [x] `routers/events.py` - Event management, attendance, voting
- [x] `routers/projects.py` - Project CRUD, collaboration
- [x] `routers/admin.py` - Admin endpoints for event owners

**Removed (obsolete):**
- [x] `routers/cache_invalidate.py` - No longer needed
- [x] `routers/test_routes.py` - Airtable-specific test endpoints
- [x] `middleware.py` - Cache instrumentation middleware
- [x] `backend/podium/cache/` - Entire cache layer deleted
- [x] `backend/CACHING.md` - Cache documentation deleted
- [x] `backend/loadtest/` - Load test scripts deleted (depended on removed endpoints)

**Updated:**
- [x] `db/__init__.py` - Exports Postgres models only
- [x] `main.py` - Removed Redis/cache initialization
- [x] `frontend/tests/helpers/api.ts` - Updated to use `event_id` (UUID) instead of `event` (list)

---

## Phase 3.5: Code Quality Cleanup ✅

Addressed typing issues and improved code patterns based on SQLModel FastAPI guide.

**Typing Improvements:**
- [x] Added typed query helpers `scalar_one_or_none()` and `scalar_all()` in `db/postgres/base.py`
- [x] Changed to `sqlmodel.ext.asyncio.session.AsyncSession` for better typing
- [x] Use `session.get()` for primary key lookups instead of `select().where(id=...)`

**Code Style Improvements:**
- [x] Use `Model.model_validate(input, update={...})` for creating models (instead of manual field assignment)
- [x] Use `model.sqlmodel_update()` with `model_dump(exclude_unset=True, exclude_none=True)` for updates
- [x] Removed unnecessary `session.add()` calls after relationship changes

**Schema Fixes:**
- [x] Removed unused `slug` field from `EventCreate` (slug is computed from name)
- [x] Added `default_factory=uuid4` to all model `id` fields (was missing, caused null ID errors)
- [x] Made `UserSignup` optional fields accept `None` (frontend sends null for empty fields)

**Config Changes:**
- [x] Made Airtable config settings optional (only needed for migration script)
- [x] Removed Redis config requirement
- [x] Made `database_url` required

---

## Phase 3.6: E2E Tests ✅

**Status:** All 7 tests pass against local Postgres.

**Fixes made:**
- [x] Fixed UUID generation in all SQLModel models (added `default_factory=uuid4`)
- [x] Fixed `UserSignup` schema to accept `None` values for optional fields
- [x] Updated frontend type imports after OpenAPI client regeneration
- [x] Updated AGENTS.md to use `npx` instead of `bunx` for Playwright

**Run tests:**
```bash
cd frontend && doppler run --config dev -- npx playwright test
```

---

## Phase 4: Dry-run on Prod Airtable 🔲

**Status:** Not started

Before production cutover, need to:
1. Run backfill script against current production Airtable data
2. Verify all records migrate correctly
3. Compare row counts
4. Test app functionality against migrated data

**Blockers:**
- Need production database connection configured
- Should verify prod Postgres on Coolify is ready

---

## Phase 5: Cutover 🔲

1. Export Airtable data (CSV backup)
2. Schedule 15-30 min maintenance window
3. Run migrations: `doppler run --config prod -- alembic upgrade head`
4. Run backfill: `doppler run --config prod -- python scripts/migrate_from_airtable.py`
5. Verify row counts
6. Deploy v2 (Postgres-only code)
7. Regenerate frontend OpenAPI client: `cd frontend && bun run openapi-ts`
8. Smoke test: login, create event, vote, leaderboard
9. Monitor 24-48 hours

---

## Phase 6: Cleanup 🔄 (Partial)

- [x] Delete `backend/podium/cache/` directory
- [x] Delete `backend/CACHING.md`
- [x] Delete `backend/loadtest/` (Airtable-specific)
- [x] Delete `routers/cache_invalidate.py` and `routers/test_routes.py`
- [x] Delete `middleware.py`
- [x] Make Airtable config optional in `config.py`
- [ ] Remove Redis/Valkey from Coolify (after prod cutover)
- [ ] Remove PyAirtable dependency (after prod cutover)
- [ ] Delete old Airtable model files (`db/db.py`, `db/user.py`, etc.) (after prod cutover)
- [ ] Remove `airtable_id` fields (optional, after prod cutover)

---

## Admin Panel: Mathesar ✅ (Preferred)

Using [Mathesar](https://mathesar.org/) as a spreadsheet-like admin UI for Postgres. Clean, focused, open-source (nonprofit).

**Why Mathesar over NocoDB:**
- Specifically designed for Postgres (not multi-database)
- Uses native Postgres roles for access control
- Cleaner UI, less clutter
- 100% open source, nonprofit-maintained

### Local Setup (Docker)

```bash
# Ensure network exists
docker network create podium-net 2>/dev/null || true
docker network connect podium-net podium-pg 2>/dev/null || true

# Create Mathesar's internal database
docker exec podium-pg psql -U postgres -c "CREATE DATABASE mathesar_django;" 2>/dev/null || true

# Run Mathesar
docker run -d \
  --name mathesar \
  --network podium-net \
  -p 8084:8000 \
  -e POSTGRES_HOST=podium-pg \
  -e POSTGRES_PORT=5432 \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=localpass \
  -e POSTGRES_DB=mathesar_django \
  -v mathesar_data:/var/lib/mathesar \
  mathesar/mathesar:latest
```

### Initial Setup (UI)

1. Open http://localhost:8084
2. Create admin account
3. Add database connection:
   - **Host:** `podium-pg`
   - **Port:** `5432`
   - **Database:** `podium`
   - **Role:** `postgres`
   - **Password:** `localpass`

### Bootstrap Script (Skip UI Setup)

For automated/reproducible setup, use the bootstrap script:

```bash
cat backend/scripts/bootstrap_mathesar.py | docker exec -i mathesar python /code/manage.py shell
```

This creates:
- Admin user: `admin` / `admin123`
- Database connection to `podium` on `podium-pg:5432`

### Quick Commands

```bash
# Start/stop Mathesar
docker start mathesar
docker stop mathesar

# View logs
docker logs mathesar

# Remove (keeps data in volume)
docker rm mathesar

# Re-run bootstrap after fresh container
cat backend/scripts/bootstrap_mathesar.py | docker exec -i mathesar python /code/manage.py shell
```

### Notes

- Mathesar uses Postgres permissions for access control
- Can create multiple user accounts with different Postgres roles
- Supports data explorer for ad-hoc queries
- No way to fully pre-configure via env vars (requires UI or bootstrap script)

---

## Production Mathesar (Coolify)

Deploy as a separate Docker Compose resource on Coolify with its own internal Postgres.

**Files:** `mathesar/` directory

### Architecture

```
┌─────────────────────────────────────────────────────┐
│ Mathesar Docker Compose                             │
│  ┌─────────────┐  ┌───────────────────────────────┐ │
│  │ mathesar-db │◄─│ mathesar                      │ │
│  │ (metadata)  │  │ (custom image: Doppler +      │ │
│  └─────────────┘  │  bootstrap + Mathesar)        │ │
│                   └───────────────┬───────────────┘ │
└───────────────────────────────────┼─────────────────┘
                                    │ connects to
                                    ▼
                       ┌─────────────────────────┐
                       │ Podium Postgres         │
                       │ (existing Coolify DB)   │
                       └─────────────────────────┘
```

### Doppler Secrets (Required)

| Secret | Description |
|--------|-------------|
| `POSTGRES_PASSWORD` | Password for Mathesar's internal database (new) |
| `MATHESAR_ADMIN_PASSWORD` | Mathesar admin user password (new) |
| `PODIUM_DATABASE_URL` | Podium Postgres URL (already exists - same as backend) |

Optional (have defaults in bootstrap.py):
- `MATHESAR_ADMIN_USERNAME` (default: `admin`)
- `MATHESAR_ADMIN_EMAIL` (default: `admin@podium.hackclub.com`)

### Coolify Environment Variables

| Variable | Description |
|----------|-------------|
| `DOPPLER_TOKEN` | Service token for Doppler (that's it!) |

### Deployment Steps

1. Add secrets to Doppler project (e.g., `podium` project, `prd_mathesar` config)
2. Create Doppler Service Token for the config
3. Create new Docker Compose resource in Coolify
4. Point to `mathesar/` directory in repo
5. Set only `DOPPLER_TOKEN` in Coolify env vars
6. Deploy

### How It Works

Both containers use custom images with Doppler CLI:

1. `mathesar-db` builds from `Dockerfile.postgres`:
   - Extends `postgres:17-alpine`
   - Adds Doppler CLI
   - Wrapper entrypoint runs `doppler run -- docker-entrypoint.sh`
   - Fetches `POSTGRES_PASSWORD` from Doppler at startup

2. `mathesar` builds from `Dockerfile`:
   - Extends `mathesar/mathesar:latest`
   - Adds Doppler CLI
   - On startup, `doppler run --` injects all secrets, then `entrypoint.sh`:
     - Runs `bootstrap.py` (creates admin user + Podium DB connection if needed)
     - Starts Mathesar with `./bin/mathesar run -nse`

No separate init container - bootstrap runs on every startup but is idempotent.

---

## Alternative: NocoDB

NocoDB also works but is more complex (multi-base, multi-tenant design). If you prefer it:

```bash
docker run -d \
  --name nocodb \
  --network podium-net \
  -p 8080:8080 \
  -v nocodb_data:/usr/app/data \
  nocodb/nocodb:latest
```

Then connect to external database in UI with `sslmode=disable` parameter.

---

## Known Gaps

### Production Admin
For production admin access:
- Deploy Mathesar on Coolify pointing to prod Postgres
- Or use Coolify's built-in database UI
- Or direct psql access for quick fixes

---

## Files

| File | Status |
|------|--------|
| `db/postgres/__init__.py` | ✅ Exports all models + query helpers |
| `db/postgres/base.py` | ✅ Async engine + session + typed helpers |
| `db/postgres/links.py` | ✅ M2M junction tables |
| `db/postgres/user.py` | ✅ User model + schemas (with uuid4 default) |
| `db/postgres/event.py` | ✅ Event model + schemas (with uuid4 default) |
| `db/postgres/project.py` | ✅ Project model + schemas (with uuid4 default) |
| `db/postgres/vote.py` | ✅ Vote model (with uuid4 default) |
| `db/postgres/referral.py` | ✅ Referral model (with uuid4 default) |
| `migrations/env.py` | ✅ Simplified Alembic config |
| `migrations/versions/*.py` | ✅ Initial migration |
| `scripts/migrate_from_airtable.py` | ✅ Complete, tested locally |
| `routers/auth.py` | ✅ Refactored with typed helpers |
| `routers/users.py` | ✅ Refactored, handles None values |
| `routers/events.py` | ✅ Refactored with session.get() and typed helpers |
| `routers/projects.py` | ✅ Refactored with model_validate/sqlmodel_update |
| `routers/admin.py` | ✅ Refactored with typed helpers |
| `config.py` | ✅ Airtable optional, database_url required |

---

## Rollback Plan

**Rollback = redeploy v1** (Airtable code).

Data created in Postgres during v2 window would be lost. Keep cutover window short.

---

## Open Questions

1. ~~**Admin UI:** Build SvelteKit pages or use Retool?~~ → Using NocoDB
2. ~~Airtable sync: Keep read-only for analytics?~~ (drop entirely)
3. IDs: Keep exposing UUIDs or generate short IDs? (keep UUIDs for now)
4. **Prod DB:** Is Coolify Postgres ready and configured in Doppler?
