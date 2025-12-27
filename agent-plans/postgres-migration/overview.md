# PostgreSQL Migration Overview (Podium v2)

**Status:** In Progress  
**Effort:** 2-3 days  
**Last Updated:** 2025-01-27

---

## What We're Doing

**Clean break** from Airtable → PostgreSQL. No feature flags, no dual backends.

| v1 (Current) | v2 (Target) |
|--------------|-------------|
| Airtable (5 req/sec limit) | PostgreSQL |
| Redis cache (workaround) | No cache needed |
| PyAirtable + Pydantic | ormar ORM |

---

## Progress

| Phase | Status |
|-------|--------|
| 1. Schema & Infrastructure | 🟡 Models drafted |
| 2. Backfill Script | ⬜ Not started |
| 3. Refactor to Postgres | ⬜ Not started |
| 4. Cutover | ⬜ Not started |
| 5. Cleanup | ⬜ Not started |

---

## Database Strategy

**One production Postgres instance. Everything else is local/ephemeral.**

| Environment | Database |
|-------------|----------|
| Local dev | Docker Postgres 17 |
| CI (GitHub Actions) | Ephemeral Postgres 17 |
| Production | `postgres-prod` (v17) on Coolify |

**Secrets:** Doppler only. No `.secrets.toml` or `.env` files.

---

## Phases

### Phase 1: Schema & Infrastructure
- [x] Draft ormar models with `airtable_id` for backfill mapping
- [ ] Split models per-entity (user.py, event.py, etc.)
- [ ] Set up Alembic migrations
- [ ] Create `postgres-prod` on Coolify
- [ ] Add Postgres service to GitHub Actions

### Phase 2: Backfill Script
- [ ] Create `scripts/migrate_from_airtable.py`
- [ ] Migrate: Users → Events → Attendees → Projects → Collaborators → Referrals → Votes
- [ ] Validate row counts match Airtable

### Phase 3: Refactor to Postgres
- [ ] Replace Airtable calls in routers with ormar queries
- [ ] Remove cache layer usage
- [ ] Update tests to use Postgres

### Phase 4: Cutover
1. Schedule 15-30 min maintenance window
2. Run Alembic migrations on prod
3. Run backfill script
4. Deploy v2 (Postgres-only code)
5. Smoke test: login, create event, vote, leaderboard
6. Monitor 24-48 hours

### Phase 5: Cleanup
- [ ] Delete `cache/` directory
- [ ] Remove Redis from Coolify
- [ ] Remove PyAirtable dependency
- [ ] Delete old Airtable model code

---

## Rollback

**Rollback = redeploy v1** (Airtable code) and point traffic back.

Data created in Postgres during v2 window would be lost. Keep cutover window short.

---

## Files

| File | Status |
|------|--------|
| `db/models_ormar.py` | ✅ Draft |
| `db/user.py`, `event.py`, etc. | ⬜ Refactor to ormar |
| `scripts/migrate_from_airtable.py` | ⬜ Not started |
| `migrations/` (Alembic) | ⬜ Not started |

---

## Open Questions

1. **Admin UI:** Build SvelteKit pages or use Retool?
2. **Airtable sync:** Keep read-only for analytics or drop entirely?
3. **IDs:** Expose UUIDs or generate short IDs?

---

See [technical.md](./technical.md) for implementation details.
