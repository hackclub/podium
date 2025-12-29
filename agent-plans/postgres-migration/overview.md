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

## Known Gaps

### App-wide Admin Panel
Currently only event-specific admin exists (`/events/admin`). No app-wide admin for:
- Viewing all users
- Viewing all events
- Manual data fixes
- Analytics dashboard

**Options:**
1. Build SvelteKit admin pages
2. Use external tool (Retool, AdminJS)
3. Direct database access via pgAdmin/Coolify

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

1. **Admin UI:** Build SvelteKit pages or use Retool? (needs decision)
2. ~~Airtable sync: Keep read-only for analytics?~~ (drop entirely)
3. IDs: Keep exposing UUIDs or generate short IDs? (keep UUIDs for now)
4. **Prod DB:** Is Coolify Postgres ready and configured in Doppler?
