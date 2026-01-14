# Database

PostgreSQL with async SQLModel ORM. Models live in `backend/podium/db/postgres/`.

## Query Patterns

Use `session.get()` for primary key lookups:
```python
event = await session.get(Event, event_id)
```

Use typed helpers for other queries:
```python
from podium.db.postgres import scalar_one_or_none, scalar_all

event = await scalar_one_or_none(session, select(Event).where(Event.slug == slug))
projects = await scalar_all(session, select(Project).where(Project.event_id == id))
```

Create models with `model_validate`:
```python
new_event = Event.model_validate(event_create, update={"owner_id": user.id})
session.add(new_event)
await session.commit()
```

Update models with `sqlmodel_update`:
```python
event.sqlmodel_update(event_update.model_dump(exclude_unset=True, exclude_none=True))
await session.commit()
```

## Eager Loading

Without eager loading, accessing a relationship triggers a separate query (N+1 problem). Use `selectinload` to fetch related records in one query:

```python
# Bad: each project.votes access triggers a query
projects = await scalar_all(session, select(Project))
for p in projects:
    print(p.votes)  # N additional queries

# Good: votes loaded upfront with one extra query
projects = await scalar_all(
    session,
    select(Project).options(selectinload(Project.votes))
)
```

See [SQLAlchemy loading docs](https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html#relationship-loading-techniques).

## Computed Fields

Use `@computed_field` for derived values from relationships. Must eager-load the relationship first:

```python
# Model
@computed_field
@property
def points(self) -> int:
    return len(self.votes)

# Query - must include selectinload
stmt = select(Project).options(selectinload(Project.votes))
```

See [Pydantic computed_field docs](https://docs.pydantic.dev/latest/concepts/fields/#computed-fields).

## Migrations

```bash
# Apply
doppler run --config dev -- uv run alembic upgrade head

# Generate after model changes
doppler run --config dev -- uv run alembic revision --autogenerate -m "description"

# Rollback
doppler run --config dev -- uv run alembic downgrade -1
```

If two branches create migrations from the same base, edit the second migration's `down_revision` to chain them.

## Reset

```bash
./scripts/reset-migrate.sh                 # Reset local DB (empty)
./scripts/reset-migrate.sh --sync <URL>    # Sync from another Postgres
```
