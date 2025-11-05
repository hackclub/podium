# Caching

Podium uses **Redis** for caching with a **zero-touch design**. The cache layer requires no changes when adding or modifying models.

## Architecture

- **Single `GenericCache` model** stores validated model data as dicts
- **8-hour TTL** with jitter to prevent thundering herd  
- **9-hour tombstones** for 404s to prevent refetch thrash
- **Schema versioning** (`v1:entity:id`) for mass invalidation on breaking changes
- **Secondary cache indexes** for high-frequency field lookups (e.g., email → user_id)

## Usage

```python
from podium import cache
from podium.cache.operations import Entity

# Get by ID
event = cache.get_one(Entity.EVENTS, id, Event)
user = cache.get_one(Entity.USERS, id, UserPrivate)

# Get by field (Airtable query)
event = cache.get_by_formula(Entity.EVENTS, {"slug": slug}, Event)

# Get user by email (optimized with secondary cache)
user = cache.get_user_by_email(email, UserPrivate)

# Get multiple by IDs
events = cache.get_many_by_ids(Entity.EVENTS, [id1, id2], Event)

# Get multiple by field (Airtable query)
projects = cache.get_many_by_formula(Entity.PROJECTS, {"event_id": id}, Project)

# Update (from webhook)
cache.upsert_entity(Entity.EVENTS, event)

# Invalidate
cache.invalidate_entity(Entity.EVENTS, id)

# Delete (from Airtable + cache)
cache.delete_entity(Entity.EVENTS, id)
```

## Adding a New Model

1. **Add to Entity enum** in `cache/operations.py`:
   ```python
   class Entity(str, Enum):
       COMMENTS = "comments"
   ```

2. **Use it** (no other cache changes):
   ```python
   comment = cache.get_one(Entity.COMMENTS, id, Comment)
   ```

## Model Changes

- **Add field**: ✅ Works automatically (Pydantic uses default)
- **Remove field**: ✅ Works automatically (filtered before validation)
- **Change type**: ✅ Triggers MISS, refetches from Airtable
- **Rename field**: ⚠️ Triggers MISS until cache expires (8h) or bump schema version

## Secondary Cache (Email Lookups)

`get_user_by_email()` implements a **three-tier lookup** to optimize the frequent "email → user" query:

1. **Secondary cache** (`v1:idx:users:email:{email}` → user_id)
2. **Primary cache** (user_id → full user data)
3. **Airtable query** (if both caches miss)

When a user is fetched, both caches are populated with the same 8hr TTL. This avoids repeated Airtable formula queries on every auth check.

**Why is this needed?** Email lookups happen on **every authenticated request** (JWT validation). Unlike ID lookups, we don't have the user_id upfront, so we'd otherwise hit Airtable repeatedly for the same user.

Other fields (slug, join codes) are queried less frequently, so they use `get_by_formula()` without secondary indexing.

## Cache Invalidation

Cache is invalidated by:
1. **Webhooks** from Airtable automations (see `cache/airtable_automation_template.js`)
2. **Delete operations** via `cache.delete_entity()`
3. **TTL expiration** (8 hours)
4. **Schema version bump** in `cache/operations.py` (invalidates all cached data)

**Note:** Secondary indexes share the same TTL as primary cache, so they expire together. Webhook invalidation clears primary cache; secondary indexes will miss and get repopulated on next lookup.

## Response Headers

- `X-Cache: HIT (3)` - Number of cache hits in this request
- `X-Cache: MISS (1)` - Number of cache misses
- `X-Cache: BYPASS` - No cache operations
- `X-Airtable-Hits: 2` - Number of Airtable API calls

## Files

- **`operations.py`** - Core cache logic (~250 lines)
- **`__init__.py`** - Public API exports
- **`client.py`** - Redis client singleton
- **`sweep.py`** - Daily orphan cleanup job
- **`README.md`** - Quick reference guide

## Best Practices

✅ **DO:**
- Use `Entity` enum for type safety
- Call `cache.delete_entity()` instead of direct Airtable deletes
- Store complete model instances (not partial views)

❌ **DON'T:**
- Don't call `tables[entity].delete()` directly (bypasses cache invalidation)
- Don't store partial/view models if you need the full data later
- Don't mix entity names (typos caught by enum)

## Bumping Schema Version

When you make breaking model changes (rename fields, remove required fields):

1. Change `CACHE_SCHEMA_VERSION = "v2"` in `cache/operations.py`
2. Restart backend
3. Old `v1:*` keys will be ignored, new `v2:*` keys will be created
