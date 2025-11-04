# Podium Cache Architecture

## Overview

Podium uses **Redis/Valkey** for caching with **zero-touch auto-configuration**. The cache layer is designed for:
- **Zero-Touch Extensibility**: Adding fields requires NO cache code changes
- **Automatic Configuration**: Cache settings auto-detected from Pydantic models  
- **Performance**: Individual record lookups are fast and cache efficiently
- **Simplicity**: No manual normalization or mapping configuration

## Key Innovation: Zero-Touch Field Addition

**Adding a new field requires ZERO cache code changes:**

```python
# Just add to your Pydantic model:
class Event(BaseEvent):
    owner: SingleRecordField  # Auto-indexed, auto-mapped to owner_id
    sponsor: str = ""         # Works automatically
    max_capacity: int = 0     # Works automatically  
    featured: bool = False    # Works automatically
```

That's it! The cache automatically:
- ✅ Stores and retrieves the field
- ✅ Indexes it (if `SingleRecordField`)
- ✅ Maps it to Airtable (if `SingleRecordField` → `field_id`)
- ✅ Normalizes/denormalizes it correctly

## Auto-Detection System

The system auto-detects cache behavior from your Pydantic models using `podium/cache/auto_config.py`:

### Automatic Indexing
- **`SingleRecordField`** → automatically indexed & mapped to `*_id`
- **`Field(json_schema_extra={"indexed": True})`** → indexed for queries
- **Scalar fields** → not indexed (unless explicitly marked)

### Automatic Sorting
- **`Field(json_schema_extra={"sortable": True})`** → sortable in Redis

### Automatic Normalization
- **`SingleRecordField`** → flattened from `['recXYZ']` to `'recXYZ'` for Redis indexing
- **`MultiRecordField`** → left as lists (not indexed)
- **Scalar fields** → no normalization needed

### Automatic Denormalization
- On read, SingleRecordFields are re-wrapped: `'recXYZ'` → `['recXYZ']`
- This happens automatically in `operations._cast_to_requested()`

## Design Principles

### 1. Cache the Richest Model

Always cache the most complete version of each entity:
- **Events**: `PrivateEvent` (includes `attendees`, `join_code`, `projects`)
- **Projects**: `PrivateProject` (includes `join_code`)
- **Users**: `UserPrivate` (includes email, relationships)

When reading, cast to the requested model type (Public/Private/Internal) from cached data.

### 2. SingleRecordField = Auto-Configured

The `SingleRecordField` type alias carries its own metadata:

```python
# In constants.py:
SingleRecordField = Annotated[
    List[Annotated[str, StringConstraints(pattern=RECORD_REGEX)]],
    Len(min_length=1, max_length=1),
    Field(json_schema_extra={"indexed": True}),  # Auto-indexed!
]
```

This means ANY field using `SingleRecordField` is automatically:
- Indexed for queries
- Mapped to Airtable `{field}_id` lookup field
- Normalized/denormalized correctly

### 3. Convention Over Configuration

Default conventions eliminate boilerplate:
- SingleRecordField `owner` → Airtable `owner_id`
- SingleRecordField `event` → Airtable `event_id`
- Scalar fields → identity mapping (`slug` → `slug`)

Override only when needed via `custom_airtable_mappings` parameter.

## Cache Operations

### Core Functions

All operations use generic functions from `cache/operations.py`:

```python
# By ID (fastest, always cached)
event = get_one("events", event_id, model=Event)
project = get_one("projects", project_id, model=PrivateProject)

# By IDs (batch)
events = get_many_by_ids("events", [id1, id2, id3], model=Event)

# By index (uses Redis indices, falls back to Airtable)
owned_events = get_by_index("events", {"owner": user_id}, model=PrivateEvent)
event_projects = get_by_index("projects", {"event": event_id}, model=Project, sort=("points", "desc"))

# Entity-specific helpers (wrap generic operations)
from podium.cache.operations import get_event, get_project, get_user

event = get_event(event_id)  # Same as get_one("events", event_id)
user = get_user_by_email(email)  # Wraps get_by_index
```

### Mutation Operations

```python
# Invalidate (remove from cache - next read fetches from Airtable)
invalidate_event(event_id)
invalidate_project(project_id)

# Upsert (update cache with latest data - for webhooks)
upsert_event(event)
upsert_project(project)

# Delete (delete from Airtable AND cache, sets tombstone)
delete_event(event_id)
delete_project(project_id)
```

## Adding a New Entity

Fully automatic! Just define your Pydantic models and register them:

### Step 1: Define Pydantic Model

```python
# In podium/db/my_entity.py
from podium.constants import SingleRecordField
from pydantic import BaseModel, Field
from typing import Annotated

class MyEntity(BaseModel):
    id: str
    name: str
    owner: SingleRecordField  # Auto-indexed → owner_id!
    category: Annotated[str, Field(json_schema_extra={"indexed": True})]
    points: Annotated[int, Field(default=0, json_schema_extra={"sortable": True})]
    description: str = ""  # Cached automatically, no config needed
```

### Step 2: Add Cache Model

```python
# In podium/cache/models.py
from podium.cache.auto_config import auto_detect_cache_config
from podium.db.my_entity import MyEntity

_my_entity_config = auto_detect_cache_config(MyEntity)

MyEntityCache = make_json_model(
    MyEntity,
    indexed_fields=_my_entity_config["indexed_fields"],  # Auto-detected!
    sortable_fields=_my_entity_config["sortable_fields"]  # Auto-detected!
)
```

### Step 3: Register Entity Spec

```python
# In podium/cache/specs.py
_my_entity_config = auto_detect_cache_config(MyEntity)

ENTITIES["my_entities"] = EntitySpec(
    name="my_entities",
    table="my_entities",
    cache_model=MyEntityCache,
    cache_pydantic=MyEntity,
    default_read_model=MyEntity,
    index_to_airtable=_my_entity_config["index_to_airtable"],  # Auto-generated!
    normalize_before_cache=_my_entity_config["normalize_fn"],   # Auto-generated!
)
```

That's it! The cache auto-detects everything from your Pydantic model.

## Cache Configuration Details

### TTL and Expiration

- **Cache TTL**: 8 hours ± 5% jitter (prevents thundering herd)
- **Tombstone TTL**: 6 hours (caches "not found" to prevent repeated 404s)

### Tombstones

When a record is deleted, a tombstone prevents repeated Airtable queries:

```
Key: tomb:{table}:{record_id}
Value: "1"
TTL: 6 hours
```

## Cache Invalidation

### Automatic (Webhooks)

Airtable automations POST to `/api/webhooks/airtable` on record changes:

```python
# Webhook handler invalidates cache automatically
@router.post("/airtable")
def airtable_webhook(payload: WebhookPayload):
    if payload.action == "update":
        invalidate_entity(payload.entity, payload.record_id)
    elif payload.action == "delete":
        delete_entity(payload.entity, payload.record_id)
```

### Manual

After direct Airtable updates (e.g., via admin panel):

```python
invalidate_event(event_id)  # Next read fetches from Airtable
```

## Cache Status Headers

Responses include cache telemetry:

```
X-Cache: HIT          # Served from cache
X-Cache: MISS         # Fetched from Airtable
X-Cache: BYPASS       # No cache operation
X-Airtable-Hits: 2    # Number of Airtable API calls
```

## Performance Characteristics

### What Caches Well ✅

- **Individual record lookups**: `get_event(id)`, `get_project(id)`
- **Batch by-ID fetches**: `get_events_by_ids([id1, id2])`
- **Index queries with Redis indices**: `get_events_by_owner(user_id)` (after first fetch)

### What Doesn't Cache Well ⚠️

- **First-time index queries**: Fall back to Airtable, then cache individual records
- This is acceptable - subsequent by-ID lookups are fast

### Optimization Pattern

When you have IDs, use them directly:

```python
# ❌ Don't do this (index query every time)
owned_events = get_events_by_owner(user.id)

# ✅ Do this (by-ID lookup, user already has IDs)
owned_events = get_events_by_ids(user.owned_events)
```

## Troubleshooting

### Cache Always Misses

1. Check Redis connection: `redis-cli ping`
2. Verify indices exist (created at startup via `Migrator().run()`)
3. Check cache TTL (records expire after 8 hours)

### Stale Data

1. Verify Airtable webhooks are configured
2. Manual invalidation: `invalidate_entity(entity, record_id)`
3. Flush cache (dev only): `redis-cli FLUSHDB`

### Type Validation Errors

- Ensure `cache_pydantic` in `EntitySpec` is the **richest model** (Private/Internal)
- Check that all required fields are present in Airtable

## Related Files

- [`cache/auto_config.py`](./podium/cache/auto_config.py) - Auto-detection logic
- [`cache/operations.py`](./podium/cache/operations.py) - Core cache operations
- [`cache/specs.py`](./podium/cache/specs.py) - Entity specifications
- [`cache/models.py`](./podium/cache/models.py) - Redis-OM JsonModels
- [`cache/client.py`](./podium/cache/client.py) - Redis client singleton
- [`constants.py`](./podium/constants.py) - SingleRecordField definition
- [`main.py`](./podium/main.py) - Cache middleware and startup
