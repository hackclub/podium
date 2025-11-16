"""Async cache operations using plain Redis.

Zero-touch: adding/changing models requires NO cache code changes.
Just use await get_one(Entity.EVENTS, id, Event) for any entity.
"""

import json
import random
from contextvars import ContextVar
from enum import Enum
from typing import Iterable, List, Optional, Type, TypeVar
import asyncio

from pydantic import BaseModel, Field
from pyairtable.formulas import match

from podium.config import settings
from podium.db import tables

# Import middleware cache stats
try:
    from podium.middleware import cache_stats
except ImportError:
    # Fallback if middleware not loaded
    cache_stats: ContextVar[dict] = ContextVar("cache_stats", default={"hits": 0, "misses": 0, "airtable_calls": 0})

TModel = TypeVar("TModel", bound=BaseModel)


class Entity(str, Enum):
    """Entity names for type safety and autocomplete."""
    EVENTS = "events"
    PROJECTS = "projects"
    USERS = "users"
    VOTES = "votes"
    REFERRALS = "referrals"


# Cache schema version - bump this to invalidate all cached data
CACHE_SCHEMA_VERSION = "v2"

# Cache TTL: 8 hours with ±5% jitter
CACHE_TTL_SECONDS = 8 * 60 * 60
# Tombstone TTL >= cache TTL to prevent deleted item refetch thrash
TOMBSTONE_TTL_SECONDS = 9 * 60 * 60

# Context variable to track cache hits/misses per request
_cache_status: ContextVar[dict] = ContextVar("cache_status")


def _mark_cache(status: str) -> None:
    """Mark cache status for the current request."""
    state = _cache_status.get(None)
    if state is None:
        return
    state["value"] = status
    key = {"HIT": "hits", "MISS": "misses", "BYPASS": "bypass"}.get(status)
    if key:
        state[key] = state.get(key, 0) + 1


def _get_ttl() -> int:
    """Get TTL with random jitter to prevent thundering herd."""
    return int(CACHE_TTL_SECONDS * random.uniform(0.95, 1.05))


# ===== TOMBSTONES =====


async def _set_tombstone(entity: str, record_id: str):
    """Set a tombstone marker for a deleted/missing record."""
    try:
        from podium.cache.client import get_redis_client

        client = get_redis_client()
        tombstone_key = f"tomb:{entity}:{record_id}"
        await client.setex(tombstone_key, TOMBSTONE_TTL_SECONDS, "1")
    except Exception:
        pass


async def _check_tombstone(entity: str, record_id: str) -> bool:
    """Check if a tombstone exists for this record."""
    try:
        from podium.cache.client import get_redis_client

        client = get_redis_client()
        tombstone_key = f"tomb:{entity}:{record_id}"
        return await client.exists(tombstone_key) > 0
    except Exception:
        return False


# ===== CACHE HELPERS =====


async def _cache_get(entity: str, record_id: str) -> Optional[dict]:
    """Get from cache, return None if not found."""
    try:
        from podium.cache.client import get_redis_client
        client = get_redis_client()
        key = f"{CACHE_SCHEMA_VERSION}:{entity}:{record_id}"
        raw = await client.get(key)
        if not raw:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        
        # Track cache hit
        try:
            stats = cache_stats.get()
            stats["hits"] = stats.get("hits", 0) + 1
            cache_stats.set(stats)
        except Exception:
            pass
        
        return json.loads(raw)
    except Exception:
        return None


async def _cache_save(entity: str, data: dict) -> None:
    """Save to cache with TTL."""
    try:
        from podium.cache.client import get_redis_client
        client = get_redis_client()
        key = f"{CACHE_SCHEMA_VERSION}:{entity}:{data['id']}"
        payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        await client.setex(key, _get_ttl(), payload)
    except Exception:
        pass


async def _cache_delete(entity: str, record_id: str) -> None:
    """Delete from cache."""
    try:
        from podium.cache.client import get_redis_client
        client = get_redis_client()
        key = f"{CACHE_SCHEMA_VERSION}:{entity}:{record_id}"
        await client.delete(key)
    except Exception:
        pass


async def _cache_secondary_get(entity: str, field: str, value: str) -> Optional[str]:
    """Get record ID from secondary index (field -> record_id mapping)."""
    try:
        from podium.cache.client import get_redis_client
        
        client = get_redis_client()
        key = f"{CACHE_SCHEMA_VERSION}:idx:{entity}:{field}:{value}"
        record_id = await client.get(key)
        if record_id:
            return record_id.decode() if isinstance(record_id, bytes) else record_id
        return None
    except Exception:
        return None


async def _cache_secondary_save(entity: str, field: str, value: str, record_id: str) -> None:
    """Save secondary index mapping (field -> record_id) with TTL."""
    try:
        from podium.cache.client import get_redis_client
        
        client = get_redis_client()
        key = f"{CACHE_SCHEMA_VERSION}:idx:{entity}:{field}:{value}"
        await client.setex(key, _get_ttl(), record_id)
    except Exception:
        pass


def _to_model(model: Type[TModel], data: dict) -> TModel:
    """Convert dict to Pydantic model (ignoring extra fields for cache compatibility)."""
    # Filter to only fields the model expects (handles removed fields gracefully)
    known_fields = set(model.model_fields.keys())
    filtered_data = {k: v for k, v in data.items() if k in known_fields}
    return model.model_validate(filtered_data)


# ===== CORE API (USE THESE FOR ALL ENTITIES) =====


async def get_one(entity: str, record_id: str, model: Type[TModel]) -> Optional[TModel]:
    """
    Get single entity by ID from cache or Airtable.

    Args:
        entity: Entity name (must match Airtable table key, e.g. "events", "projects")
        record_id: Airtable record ID
        model: Pydantic model type to validate/return

    Returns:
        Validated model instance or None if not found

    Example:
        event = await get_one("events", "rec123", Event)
        user = await get_one("users", "rec456", UserPrivate)
    """
    # Check tombstone
    if await _check_tombstone(entity, record_id):
        _mark_cache("HIT")
        return None

    # Try cache
    cached = await _cache_get(entity, record_id)
    if cached:
        _mark_cache("HIT")
        try:
            return _to_model(model, cached)
        except Exception:
            # Validation failed - fall through to refetch
            pass

    # Cache miss - fetch from Airtable (run in thread pool to avoid blocking)
    _mark_cache("MISS")
    try:
        loop = asyncio.get_event_loop()
        record = await loop.run_in_executor(None, tables[entity].get, record_id)
        fields = {**record["fields"], "id": record["id"]}
        validated = _to_model(model, fields)
        await _cache_save(entity, validated.model_dump())
        return validated
    except Exception as e:
        if "404" in str(e) or "not found" in str(e).lower():
            await _set_tombstone(entity, record_id)
        return None


async def get_many_by_ids(
    entity: str, ids: Iterable[str], model: Type[TModel]
) -> List[TModel]:
    """
    Get multiple entities by IDs from cache; batch-fetch all misses from Airtable.
    Preserves input order and drops missing.

    Args:
        entity: Entity name
        ids: Iterable of Airtable record IDs
        model: Pydantic model type

    Returns:
        List of validated model instances (in same order as input IDs)

    Example:
        events = await get_many_by_ids("events", ["rec1", "rec2"], Event)
    """
    out: List[TModel] = []
    ids_list = list(ids)
    if not ids_list:
        return out

    results_map: dict[str, TModel] = {}
    misses: List[str] = []

    # First try cache (and skip tombstoned) - run all checks concurrently
    tombstone_checks = await asyncio.gather(*[_check_tombstone(entity, rid) for rid in ids_list])
    cache_gets = await asyncio.gather(*[_cache_get(entity, rid) for rid in ids_list])
    
    for i, rid in enumerate(ids_list):
        if tombstone_checks[i]:
            continue
        cached = cache_gets[i]
        if cached:
            try:
                results_map[rid] = _to_model(model, cached)
            except Exception:
                misses.append(rid)
        else:
            misses.append(rid)

    # Batch fetch misses via OR(RECORD_ID()='...') in safe chunks
    if misses:
        def chunks(seq: List[str], size: int):
            for i in range(0, len(seq), size):
                yield seq[i : i + size]

        loop = asyncio.get_event_loop()
        for chunk in chunks(misses, 50):
            formula = "OR(" + ",".join([f"RECORD_ID()='{rid}'" for rid in chunk]) + ")"
            try:
                records = await loop.run_in_executor(None, tables[entity].all, formula)
                # Cache all results concurrently
                save_tasks = []
                for r in records:
                    fields = {**r["fields"], "id": r["id"]}
                    validated = _to_model(model, fields)
                    save_tasks.append(_cache_save(entity, validated.model_dump()))
                    results_map[validated.id] = validated
                await asyncio.gather(*save_tasks)
            except Exception:
                # Ignore chunk errors; missing ones will just be skipped
                pass

    # Preserve input order; drop missing
    for rid in ids_list:
        item = results_map.get(rid)
        if item is not None:
            out.append(item)
    return out


async def get_by_formula(
    entity: str, formula_dict: dict, model: Type[TModel]
) -> Optional[TModel]:
    """
    Query Airtable by formula and cache the first result.

    Args:
        entity: Entity name (use Entity enum for type safety)
        formula_dict: Dict for pyairtable.formulas.match()
        model: Pydantic model type

    Returns:
        First matching record or None

    Example:
        user = await get_by_formula(Entity.USERS, {"email": "test@example.com"}, UserPrivate)
        event = await get_by_formula(Entity.EVENTS, {"slug": "my-event"}, Event)
    """
    _mark_cache("MISS")
    try:
        loop = asyncio.get_event_loop()
        records = await loop.run_in_executor(None, tables[entity].all, match(formula_dict))
        if not records:
            return None
        fields = {**records[0]["fields"], "id": records[0]["id"]}
        validated = _to_model(model, fields)
        await _cache_save(entity, validated.model_dump())
        return validated
    except Exception:
        return None


async def get_many_by_formula(
    entity: str, formula_dict: dict, model: Type[TModel]
) -> List[TModel]:
    """
    Query Airtable by formula and cache all results.

    Args:
        entity: Entity name (use Entity enum for type safety)
        formula_dict: Dict for pyairtable.formulas.match()
        model: Pydantic model type

    Returns:
        List of matching records

    Example:
        projects = await get_many_by_formula(Entity.PROJECTS, {"event_id": "rec123"}, Project)
        votes = await get_many_by_formula(Entity.VOTES, {"event_id": "rec123"}, Vote)
    """
    try:
        loop = asyncio.get_event_loop()
        records = await loop.run_in_executor(None, tables[entity].all, match(formula_dict))
        out: List[TModel] = []
        save_tasks = []
        for r in records:
            fields = {**r["fields"], "id": r["id"]}
            validated = _to_model(model, fields)
            save_tasks.append(_cache_save(entity, validated.model_dump()))
            out.append(validated)
        await asyncio.gather(*save_tasks)
        return out
    except Exception:
        return []


async def upsert_entity(entity: str, obj: BaseModel) -> None:
    """
    Update or insert entity in cache (called by webhook).

    Args:
        entity: Entity name
        obj: Pydantic model instance

    Example:
        await upsert_entity("events", event)
    """
    await _cache_save(entity, obj.model_dump())


async def invalidate_entity(entity: str, record_id: str) -> None:
    """
    Remove entity from cache (called by webhook or delete).

    Args:
        entity: Entity name
        record_id: Airtable record ID

    Example:
        await invalidate_entity("events", "rec123")
    """
    await _cache_delete(entity, record_id)


async def delete_entity(entity: str, record_id: str) -> None:
    """
    Delete entity from Airtable and invalidate cache.

    Args:
        entity: Entity name
        record_id: Airtable record ID

    Example:
        await delete_entity("events", "rec123")
    """
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, tables[entity].delete, record_id)
    await invalidate_entity(entity, record_id)
    await _set_tombstone(entity, record_id)


async def get_user_by_email(email: str, model: Type[TModel]) -> Optional[TModel]:
    """
    Get user by email using secondary cache for efficient lookups.

    This function implements a three-tier lookup:
    1. Check secondary cache (email -> user_id mapping)
    2. Check primary cache (user_id -> user data)
    3. Query Airtable and cache results

    Args:
        email: User email address (will be normalized)
        model: Pydantic model type (UserInternal, UserPrivate, etc.)

    Returns:
        Validated user model or None if not found

    Example:
        user = await get_user_by_email("test@example.com", UserInternal)
    """
    # Normalize email
    email = email.lower().strip()
    
    # Check secondary cache for email -> user_id mapping
    user_id = await _cache_secondary_get(Entity.USERS, "email", email)
    if user_id:
        # Try primary cache with the user_id
        user = await get_one(Entity.USERS, user_id, model)
        if user:
            return user
    
    # Fall back to Airtable query
    _mark_cache("MISS")
    try:
        loop = asyncio.get_event_loop()
        records = await loop.run_in_executor(None, tables[Entity.USERS].all, match({"email": email}))
        if not records:
            return None
        
        fields = {**records[0]["fields"], "id": records[0]["id"]}
        validated = _to_model(model, fields)
        
        # Cache both primary and secondary
        await _cache_save(Entity.USERS, validated.model_dump())
        await _cache_secondary_save(Entity.USERS, "email", email, validated.id)
        
        return validated
    except Exception:
        return None
