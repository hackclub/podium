"""Simplified cache operations using a single generic Redis-OM model.

Zero-touch: adding/changing models requires NO cache code changes.
Just use get_one(Entity.EVENTS, id, Event) for any entity.
"""

import random
from contextvars import ContextVar
from enum import Enum
from typing import Iterable, List, Optional, Type, TypeVar

from pydantic import BaseModel
from pyairtable.formulas import match
from redis_om import JsonModel, get_redis_connection

from podium.config import settings
from podium.db import tables

TModel = TypeVar("TModel", bound=BaseModel)


class Entity(str, Enum):
    """Entity names for type safety and autocomplete."""
    EVENTS = "events"
    PROJECTS = "projects"
    USERS = "users"
    VOTES = "votes"
    REFERRALS = "referrals"


# Cache schema version - bump this to invalidate all cached data
CACHE_SCHEMA_VERSION = "v1"

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


# ===== GENERIC CACHE MODEL =====

_redis_conn = get_redis_connection(url=settings.redis_url, decode_responses=False)


class GenericCache(JsonModel):
    """Single generic cache model storing raw dicts."""

    pk: str  # Format: "{entity}:{record_id}"
    entity: str
    data: dict

    class Meta:
        database = _redis_conn


# ===== TOMBSTONES =====


def _set_tombstone(entity: str, record_id: str):
    """Set a tombstone marker for a deleted/missing record."""
    try:
        from podium.cache.client import get_redis_client

        client = get_redis_client()
        tombstone_key = f"tomb:{entity}:{record_id}"
        client.setex(tombstone_key, TOMBSTONE_TTL_SECONDS, "1")
    except Exception:
        pass


def _check_tombstone(entity: str, record_id: str) -> bool:
    """Check if a tombstone exists for this record."""
    try:
        from podium.cache.client import get_redis_client

        client = get_redis_client()
        tombstone_key = f"tomb:{entity}:{record_id}"
        return client.exists(tombstone_key) > 0
    except Exception:
        return False


# ===== CACHE HELPERS =====


def _cache_get(entity: str, record_id: str) -> Optional[dict]:
    """Get from cache, return None if not found."""
    try:
        pk = f"{CACHE_SCHEMA_VERSION}:{entity}:{record_id}"
        inst = GenericCache.get(pk)
        return inst.data if inst else None
    except Exception:
        return None


def _cache_save(entity: str, data: dict) -> None:
    """Save to cache with TTL."""
    try:
        pk = f"{CACHE_SCHEMA_VERSION}:{entity}:{data['id']}"
        inst = GenericCache(pk=pk, entity=entity, data=data)
        inst.save()
        inst.expire(_get_ttl())
    except Exception:
        pass


def _cache_delete(entity: str, record_id: str) -> None:
    """Delete from cache."""
    try:
        pk = f"{CACHE_SCHEMA_VERSION}:{entity}:{record_id}"
        GenericCache.delete(pk)
    except Exception:
        pass


def _cache_secondary_get(entity: str, field: str, value: str) -> Optional[str]:
    """Get record ID from secondary index (field -> record_id mapping)."""
    try:
        from podium.cache.client import get_redis_client
        
        client = get_redis_client()
        key = f"{CACHE_SCHEMA_VERSION}:idx:{entity}:{field}:{value}"
        record_id = client.get(key)
        return record_id.decode() if record_id else None
    except Exception:
        return None


def _cache_secondary_save(entity: str, field: str, value: str, record_id: str) -> None:
    """Save secondary index mapping (field -> record_id) with TTL."""
    try:
        from podium.cache.client import get_redis_client
        
        client = get_redis_client()
        key = f"{CACHE_SCHEMA_VERSION}:idx:{entity}:{field}:{value}"
        client.setex(key, _get_ttl(), record_id)
    except Exception:
        pass


def _to_model(model: Type[TModel], data: dict) -> TModel:
    """Convert dict to Pydantic model (ignoring extra fields for cache compatibility)."""
    # Filter to only fields the model expects (handles removed fields gracefully)
    known_fields = set(model.model_fields.keys())
    filtered_data = {k: v for k, v in data.items() if k in known_fields}
    return model.model_validate(filtered_data)


# ===== CORE API (USE THESE FOR ALL ENTITIES) =====


def get_one(entity: str, record_id: str, model: Type[TModel]) -> Optional[TModel]:
    """
    Get single entity by ID from cache or Airtable.

    Args:
        entity: Entity name (must match Airtable table key, e.g. "events", "projects")
        record_id: Airtable record ID
        model: Pydantic model type to validate/return

    Returns:
        Validated model instance or None if not found

    Example:
        event = get_one("events", "rec123", Event)
        user = get_one("users", "rec456", UserPrivate)
    """
    # Check tombstone
    if _check_tombstone(entity, record_id):
        _mark_cache("HIT")
        return None

    # Try cache
    cached = _cache_get(entity, record_id)
    if cached:
        _mark_cache("HIT")
        try:
            return _to_model(model, cached)
        except Exception:
            # Validation failed - fall through to refetch
            pass

    # Cache miss - fetch from Airtable
    _mark_cache("MISS")
    try:
        record = tables[entity].get(record_id)
        fields = {**record["fields"], "id": record["id"]}
        validated = _to_model(model, fields)
        _cache_save(entity, validated.model_dump())
        return validated
    except Exception as e:
        if "404" in str(e) or "not found" in str(e).lower():
            _set_tombstone(entity, record_id)
        return None


def get_many_by_ids(
    entity: str, ids: Iterable[str], model: Type[TModel]
) -> List[TModel]:
    """
    Get multiple entities by IDs from cache or Airtable.

    Args:
        entity: Entity name
        ids: Iterable of Airtable record IDs
        model: Pydantic model type

    Returns:
        List of validated model instances (in same order as input IDs)

    Example:
        events = get_many_by_ids("events", ["rec1", "rec2"], Event)
    """
    out: List[TModel] = []
    for rid in ids:
        item = get_one(entity, rid, model=model)
        if item is not None:
            out.append(item)
    return out


def get_by_formula(
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
        user = get_by_formula(Entity.USERS, {"email": "test@example.com"}, UserPrivate)
        event = get_by_formula(Entity.EVENTS, {"slug": "my-event"}, Event)
    """
    _mark_cache("MISS")
    try:
        records = tables[entity].all(formula=match(formula_dict))
        if not records:
            return None
        fields = {**records[0]["fields"], "id": records[0]["id"]}
        validated = _to_model(model, fields)
        _cache_save(entity, validated.model_dump())
        return validated
    except Exception:
        return None


def get_many_by_formula(
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
        projects = get_many_by_formula(Entity.PROJECTS, {"event_id": "rec123"}, Project)
        votes = get_many_by_formula(Entity.VOTES, {"event_id": "rec123"}, Vote)
    """
    try:
        records = tables[entity].all(formula=match(formula_dict))
        out: List[TModel] = []
        for r in records:
            fields = {**r["fields"], "id": r["id"]}
            validated = _to_model(model, fields)
            _cache_save(entity, validated.model_dump())
            out.append(validated)
        return out
    except Exception:
        return []


def upsert_entity(entity: str, obj: BaseModel) -> None:
    """
    Update or insert entity in cache (called by webhook).

    Args:
        entity: Entity name
        obj: Pydantic model instance

    Example:
        upsert_entity("events", event)
    """
    _cache_save(entity, obj.model_dump())


def invalidate_entity(entity: str, record_id: str) -> None:
    """
    Remove entity from cache (called by webhook or delete).

    Args:
        entity: Entity name
        record_id: Airtable record ID

    Example:
        invalidate_entity("events", "rec123")
    """
    _cache_delete(entity, record_id)


def delete_entity(entity: str, record_id: str) -> None:
    """
    Delete entity from Airtable and invalidate cache.

    Args:
        entity: Entity name
        record_id: Airtable record ID

    Example:
        delete_entity("events", "rec123")
    """
    tables[entity].delete(record_id)
    invalidate_entity(entity, record_id)
    _set_tombstone(entity, record_id)


def get_user_by_email(email: str, model: Type[TModel]) -> Optional[TModel]:
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
        user = get_user_by_email("test@example.com", UserInternal)
    """
    # Normalize email
    email = email.lower().strip()
    
    # Check secondary cache for email -> user_id mapping
    user_id = _cache_secondary_get(Entity.USERS, "email", email)
    if user_id:
        # Try primary cache with the user_id
        user = get_one(Entity.USERS, user_id, model)
        if user:
            return user
    
    # Fall back to Airtable query
    _mark_cache("MISS")
    try:
        records = tables[Entity.USERS].all(formula=match({"email": email}))
        if not records:
            return None
        
        fields = {**records[0]["fields"], "id": records[0]["id"]}
        validated = _to_model(model, fields)
        
        # Cache both primary and secondary
        _cache_save(Entity.USERS, validated.model_dump())
        _cache_secondary_save(Entity.USERS, "email", email, validated.id)
        
        return validated
    except Exception:
        return None
