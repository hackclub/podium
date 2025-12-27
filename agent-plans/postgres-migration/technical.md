# PostgreSQL Migration: Technical Details

See [overview.md](./overview.md) for context.

---

## Draft Files

All code drafts live in the `drafts/` directory:

| File | Purpose |
|------|---------|
| [models_ormar.py](./drafts/models_ormar.py) | ormar ORM models (User, Event, Project, etc.) |
| [migrate_from_airtable.py](./drafts/migrate_from_airtable.py) | One-time backfill script |
| [alembic_env.py](./drafts/alembic_env.py) | Alembic env.py configuration |
| [test.yml](./drafts/test.yml) | GitHub Actions CI with Postgres |

---

## Local Development

```bash
# Start local Postgres (one-time)
docker run --name podium-pg \
  -e POSTGRES_PASSWORD=localpass \
  -e POSTGRES_DB=podium \
  -p 5432:5432 \
  -d postgres:17

# Run migrations
doppler run --config dev -- alembic upgrade head

# Start backend
doppler run --config dev -- uv run podium
```

All secrets come from Doppler. No `.secrets.toml` or `.env` files.

---

## ormar Models

**Draft:** [drafts/models_ormar.py](./drafts/models_ormar.py)

**Final structure:** Split per-entity to match current layout:
- `db/user.py` → User model + queries
- `db/event.py` → Event model + queries
- `db/project.py` → Project model + queries
- `db/vote.py` → Vote model + queries
- `db/referral.py` → Referral model + queries

All models include `airtable_id` for backfill mapping.

### Models

| Model | Table | Relationships |
|-------|-------|---------------|
| `User` | `users` | - |
| `Event` | `events` | `owner` → User (FK), `attendees` → User (M2M) |
| `Project` | `projects` | `owner` → User (FK), `event` → Event (FK), `collaborators` → User (M2M) |
| `Vote` | `votes` | `voter` → User, `project` → Project, `event` → Event |
| `Referral` | `referrals` | `user` → User, `event` → Event |

**Note:** Many-to-many relationships (`attendees`, `collaborators`) use `ormar.ManyToMany()` - ormar auto-creates junction tables. No explicit `EventAttendee` or `ProjectCollaborator` models needed.

---

## Alembic Setup

### Install

```bash
cd backend
uv add alembic databases asyncpg psycopg2-binary
alembic init migrations
```

Then copy [drafts/alembic_env.py](./drafts/alembic_env.py) to `backend/migrations/env.py`.

### Commands

```bash
# Generate migration
doppler run --config dev -- alembic revision --autogenerate -m "description"

# Apply migrations (local)
doppler run --config dev -- alembic upgrade head

# Apply migrations (production)
doppler run --config prod -- alembic upgrade head

# Rollback one migration
doppler run --config dev -- alembic downgrade -1
```

---

## Backfill Script

**Draft:** [drafts/migrate_from_airtable.py](./drafts/migrate_from_airtable.py)

**Final location:** `backend/scripts/migrate_from_airtable.py`

**Migration order** (foreign keys must resolve):
1. Users
2. Events
3. Event attendees (M2M via `.add()`)
4. Projects
5. Project collaborators (M2M via `.add()`)
6. Referrals
7. Votes

### Run

```bash
# Local (test against local Postgres)
doppler run --config dev -- python scripts/migrate_from_airtable.py

# Production
doppler run --config prod -- python scripts/migrate_from_airtable.py
```

---

## Refactoring Routers

Replace Airtable/cache calls with direct ormar queries. No wrapper layer needed.

### Before (Airtable)

```python
from podium.db.user import get_user_by_email
from podium.cache.operations import get_one

user = get_user_by_email(email, UserPrivate)
event = get_one("events", event_id)
```

### After (Postgres)

```python
from podium.db.user import User  # ormar model

user = await User.objects.get_or_none(email=email.lower())
event = await Event.objects.select_related("owner").get_or_none(id=event_id)
```

### Common Query Patterns

```python
# Get by ID
user = await User.objects.get_or_none(id=user_id)

# Get by field
event = await Event.objects.get_or_none(slug=slug)

# With relationships
event = await Event.objects.select_related("owner").get(id=event_id)

# Filter
projects = await Project.objects.filter(event=event_id).all()

# Create
vote = await Vote.objects.create(voter=user_id, project=project_id, event=event_id)

# Update
await user.update(display_name="New Name")

# Delete
await project.delete()

# Count
count = await Vote.objects.filter(event=event_id, voter=user_id).count()
```

---

## Coolify Setup

### Production Postgres

1. **angad/podium** → **production** environment
2. **+ Add New Resource** → **Database** → **PostgreSQL**
3. Configure:
   - Name: `postgres-prod`
   - Version: `17`
   - Database: `podium`
   - Password: Generate secure password
4. **Backups** → Configure S3 destination
5. Add password to Doppler `prod` environment as `DATABASE_PASSWORD`

---

## Doppler Configuration

### Environments

| Environment | Purpose |
|-------------|---------|
| `dev` | Local development |
| `prod` | Production |

### Variables

| Variable | `dev` | `prod` |
|----------|-------|--------|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:localpass@localhost:5432/podium` | `postgresql+asyncpg://postgres:<pw>@postgres-prod:5432/podium` |
| `PODIUM_ENV` | `development` | `production` |

All existing variables (JWT secret, SendGrid, Airtable keys for backfill) remain.

---

## GitHub Actions CI

**Draft:** [drafts/test.yml](./drafts/test.yml)

Note: We don't use pytest. Frontend has Playwright E2E tests.

---

## Cutover Checklist

### Before Cutover
- [ ] ormar models finalized and split per-entity
- [ ] Alembic migrations tested locally
- [ ] Backfill script tested locally
- [ ] All routers refactored to Postgres
- [ ] `postgres-prod` created on Coolify with S3 backups

### Cutover Day
1. Export Airtable data (CSV backup)
2. Schedule 15-30 min maintenance window
3. Run migrations: `doppler run --config prod -- alembic upgrade head`
4. Run backfill: `doppler run --config prod -- python scripts/migrate_from_airtable.py`
5. Verify row counts
6. Deploy v2 (Postgres-only code)
7. Smoke test: login, create event, vote, leaderboard
8. Monitor 24-48 hours

### Post-Cutover Cleanup
- [ ] Delete `backend/podium/cache/` directory
- [ ] Remove Redis from Coolify
- [ ] Remove PyAirtable dependency
- [ ] Delete old Airtable model files
- [ ] Remove `airtable_id` fields (optional, can keep for reference)
