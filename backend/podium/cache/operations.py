"""
Cache operations with fallback to Airtable.

Implements cache-aside pattern:
1. Try to get from cache
2. On miss, fetch from Airtable
3. Store in cache for next time
4. Return validated Pydantic model
"""

import random
from contextvars import ContextVar
from typing import Any, Dict, Iterable, List, Optional, Type, TypeVar

from pydantic import BaseModel
from pyairtable.formulas import match

from podium.cache.client import get_redis_client
from podium.cache.specs import ENTITIES, EntitySpec
from podium.db import tables
from podium.db.event import BaseEvent, Event, PrivateEvent
from podium.db.project import Project, ProjectBase
from podium.db.referral import Referral
from podium.db.user import UserBase, UserPrivate
from podium.db.vote import Vote

T = TypeVar("T")
TModel = TypeVar("TModel", bound=BaseModel)

# Context variable to track cache hits/misses per request
_cache_status: ContextVar[dict] = ContextVar("cache_status")


def _mark_cache(status: str) -> None:
    """Mark cache status for the current request (safe for threadpool execution)."""
    state = _cache_status.get(None)
    if state is not None:
        state["value"] = status


# Cache TTL: 8 hours with ±5% jitter to prevent synchronized expiration
CACHE_TTL_SECONDS = 8 * 60 * 60  # 8 hours = 28800 seconds

# Tombstone TTL: 6 hours - caches "not found" to prevent repeated 404s
TOMBSTONE_TTL_SECONDS = 6 * 60 * 60  # 6 hours = 21600 seconds


def _get_ttl() -> int:
    """Get TTL with random jitter to prevent thundering herd on expiry."""
    return int(CACHE_TTL_SECONDS * random.uniform(0.95, 1.05))


def _set_tombstone(table: str, record_id: str):
    """Set a tombstone marker for a deleted record."""
    try:
        client = get_redis_client()
        tombstone_key = f"tomb:{table}:{record_id}"
        client.setex(tombstone_key, TOMBSTONE_TTL_SECONDS, "1")
    except Exception:
        pass


def _check_tombstone(table: str, record_id: str) -> bool:
    """Check if a tombstone exists for this record."""
    try:
        client = get_redis_client()
        tombstone_key = f"tomb:{table}:{record_id}"
        return client.exists(tombstone_key) > 0
    except Exception:
        return False


# ===== GENERIC CACHE OPERATIONS =====


def _to_model(model: Type[TModel], data: dict) -> TModel:
    """Convert dict to Pydantic model (v2-safe)."""
    return model.model_validate(data)


def _air_formula(spec: EntitySpec, where: Dict[str, Any]) -> Dict[str, Any]:
    """Translate cache/index fields to Airtable formula fields."""
    if not spec.index_to_airtable:
        return where
    out = {}
    for k, v in where.items():
        out[spec.index_to_airtable.get(k, k)] = v
    return out


def _cache_get(spec: EntitySpec, record_id: str) -> Optional[BaseModel]:
    """Get from cache, return None if not found."""
    try:
        cached = spec.cache_model.get(record_id)
        return cached
    except Exception:
        return None


def _cache_save(spec: EntitySpec, model: BaseModel) -> None:
    """Save to cache with TTL."""
    try:
        data = model.model_dump()
        if spec.normalize_before_cache:
            data = spec.normalize_before_cache(data)
        inst = spec.cache_model(pk=data["id"], **data)
        inst.save()
        inst.expire(_get_ttl())
    except Exception:
        pass


def _cache_delete(spec: EntitySpec, record_id: str) -> None:
    """Delete from cache."""
    try:
        spec.cache_model.delete(record_id)
    except Exception:
        pass


def _fetch_airtable_by_id(spec: EntitySpec, record_id: str) -> Optional[BaseModel]:
    """Fetch from Airtable by ID and cache."""
    try:
        table = tables[spec.table]
        record = table.get(record_id)
        fields = {**record["fields"], "id": record["id"]}
        validated = _to_model(spec.cache_pydantic, fields)
        _cache_save(spec, validated)
        return validated
    except Exception as e:
        if "404" in str(e) or "not found" in str(e).lower():
            _set_tombstone(spec.table, record_id)
        return None


def _fetch_airtable_by_index(
    spec: EntitySpec, where: Dict[str, Any]
) -> List[BaseModel]:
    """Fetch from Airtable by index query and cache."""
    try:
        table = tables[spec.table]
        formula = match(_air_formula(spec, where))
        records = table.all(formula=formula)
        out: List[BaseModel] = []
        for r in records:
            fields = {**r["fields"], "id": r["id"]}
            inst = _to_model(spec.cache_pydantic, fields)
            out.append(inst)
            _cache_save(spec, inst)
        return out
    except Exception:
        return []


def _cast_to_requested(cached: BaseModel, model: Type[TModel]) -> Optional[TModel]:
    """Cast cached model to requested model type, denormalizing SingleRecordFields."""
    try:
        from typing import get_origin
        
        data = cached.model_dump()
        
        # Re-wrap normalized string fields back to lists for SingleRecordField types
        for name, field_info in model.model_fields.items():
            if name in data and isinstance(data[name], str):
                # Check if field expects a list
                origin = get_origin(field_info.annotation)
                if origin is list:
                    # Convert string back to single-element list
                    data[name] = [data[name]]
        
        return _to_model(model, data)
    except Exception:
        return None


def get_one(
    entity: str, record_id: str, model: Optional[Type[TModel]] = None
) -> Optional[TModel]:
    """
    Get single entity by ID from cache or Airtable.

    Args:
        entity: Entity name (e.g., "projects", "events")
        record_id: Airtable record ID
        model: Model type to return (defaults to entity's default_read_model)

    Returns:
        Validated model instance or None if not found
    """
    spec = ENTITIES[entity]
    target_model = model or spec.default_read_model

    # Check tombstone first
    if _check_tombstone(spec.table, record_id):
        _mark_cache("HIT")
        return None

    # Try cache
    cached = _cache_get(spec, record_id)
    if cached:
        _mark_cache("HIT")
        casted = _cast_to_requested(cached, target_model)
        if casted is not None:
            return casted
        # Cast failed (rare) - refetch from Airtable
        _mark_cache("MISS")
        fetched = _fetch_airtable_by_id(spec, record_id)
        return _cast_to_requested(fetched, target_model) if fetched else None

    # Cache miss - fetch from Airtable
    _mark_cache("MISS")
    fetched = _fetch_airtable_by_id(spec, record_id)
    return _cast_to_requested(fetched, target_model) if fetched else None


def get_many_by_ids(
    entity: str, ids: Iterable[str], model: Optional[Type[TModel]] = None
) -> List[TModel]:
    """
    Get multiple entities by IDs from cache or Airtable.

    Args:
        entity: Entity name (e.g., "projects", "events")
        ids: Iterable of Airtable record IDs
        model: Model type to return (defaults to entity's default_read_model)

    Returns:
        List of validated model instances (in same order as input IDs)
    """
    out: List[TModel] = []
    for rid in ids:
        item = get_one(entity, rid, model=model)
        if item is not None:
            out.append(item)
    return out


def get_by_index(
    entity: str,
    where: Dict[str, Any],
    model: Optional[Type[TModel]] = None,
    sort: Optional[tuple[str, str]] = None,
) -> List[TModel]:
    """
    Get entities by indexed field query.

    Args:
        entity: Entity name (e.g., "projects", "events")
        where: Query dict (e.g., {"event": "rec123"})
        model: Model type to return (defaults to entity's default_read_model)
        sort: Optional (field_name, direction) tuple (e.g., ("points", "desc"))

    Returns:
        List of validated model instances
    """
    spec = ENTITIES[entity]
    target_model = model or spec.default_read_model

    # Try cache index
    try:
        # Build redis-om find condition: (field1 == v1) & (field2 == v2) ...
        cond = None
        for k, v in where.items():
            expr = getattr(spec.cache_model, k) == v
            cond = expr if cond is None else (cond & expr)
        query = spec.cache_model.find(cond) if cond is not None else spec.cache_model.find()
        if sort:
            field, direction = sort
            query = query.sort_by(f"{'-' if direction.lower() == 'desc' else ''}{field}")
        cached = query.all()
        if cached:
            _mark_cache("HIT")
            items = []
            for c in cached:
                casted = _cast_to_requested(c, target_model)
                if casted is not None:
                    items.append(casted)
                else:
                    # Cast failed - fall through to Airtable
                    items = []
                    break
            if items:
                return items
        # Empty result or cast failure - mark as miss
        _mark_cache("MISS")
    except Exception:
        # Exception in cache query - don't mark
        pass

    # Fetch from Airtable
    try:
        fetched = _fetch_airtable_by_index(spec, where)
        items = []
        for f in fetched:
            casted = _cast_to_requested(f, target_model)
            if casted is not None:
                items.append(casted)
    except Exception as e:
        import logging
        logging.warning(f"Cache index query failed for {entity} with {where}: {e}")
        items = []
    # Sort in Python if needed (cache couldn't sort)
    if sort and items:
        field, direction = sort
        reverse = direction.lower() == "desc"
        items.sort(key=lambda m: getattr(m, field), reverse=reverse)
    return items


def upsert_entity(entity: str, obj: BaseModel) -> None:
    """
    Update or insert entity in cache.

    Args:
        entity: Entity name (e.g., "projects", "events")
        obj: Model instance to cache
    """
    spec = ENTITIES[entity]
    _cache_save(spec, obj)


def invalidate_entity(entity: str, record_id: str) -> None:
    """
    Remove entity from cache.

    Args:
        entity: Entity name (e.g., "projects", "events")
        record_id: Airtable record ID
    """
    spec = ENTITIES[entity]
    _cache_delete(spec, record_id)


def delete_entity(entity: str, record_id: str) -> None:
    """
    Delete entity from Airtable and invalidate cache.

    Args:
        entity: Entity name (e.g., "projects", "events")
        record_id: Airtable record ID
    """
    spec = ENTITIES[entity]
    tables[spec.table].delete(record_id)
    invalidate_entity(entity, record_id)
    _set_tombstone(spec.table, record_id)


# ===== PROJECT OPERATIONS =====

P = TypeVar("P", bound=ProjectBase)


def get_project(project_id: str, model: Type[P] = Project) -> Optional[P]:
    """Get project by ID from cache or Airtable."""
    return get_one("projects", project_id, model=model)


def get_projects_for_event(
    event_id: str, sort_by_points: bool = False, model: Type[P] = Project
) -> List[P]:
    """Get all projects for an event."""
    sort = ("points", "desc") if sort_by_points else None
    return get_by_index("projects", {"event": event_id}, model=model, sort=sort)


def invalidate_project(project_id: str):
    """Remove project from cache (called by webhook)."""
    invalidate_entity("projects", project_id)


def upsert_project(project: Project):
    """Update or insert project in cache (called by webhook)."""
    upsert_entity("projects", project)


def delete_project(project_id: str):
    """Delete project from Airtable and invalidate cache."""
    delete_entity("projects", project_id)


# ===== EVENT OPERATIONS =====

E = TypeVar("E", bound=BaseEvent)


def get_event(event_id: str, model: Type[E] = Event) -> Optional[E]:
    """Get event by ID from cache or Airtable."""
    return get_one("events", event_id, model=model)


def get_event_by_slug(slug: str, model: Type[E] = Event) -> Optional[E]:
    """Get event by slug from cache or Airtable."""
    items = get_by_index("events", {"slug": slug}, model=model)
    return items[0] if items else None


def get_events_by_ids(event_ids: list[str], model: Type[E] = Event) -> list[E]:
    """Batch fetch events by IDs from cache or Airtable."""
    return get_many_by_ids("events", event_ids, model=model)


def get_events_by_owner(owner_id: str, model: Type[E] = Event) -> list[E]:
    """Get all events owned by a user using cache index."""
    return get_by_index("events", {"owner": owner_id}, model=model)


def invalidate_event(event_id: str):
    """Remove event from cache (called by webhook or delete)."""
    invalidate_entity("events", event_id)


def upsert_event(event: Event | PrivateEvent):
    """Update or insert event in cache (called by webhook)."""
    # Always cache as PrivateEvent
    if isinstance(event, PrivateEvent):
        upsert_entity("events", event)
    else:
        # Upgrade Event to PrivateEvent
        private_event = PrivateEvent(**event.dict())
        upsert_entity("events", private_event)


def delete_event(event_id: str):
    """Delete event from Airtable and invalidate cache."""
    delete_entity("events", event_id)


# ===== USER OPERATIONS =====

U = TypeVar("U", bound=UserBase)


def get_user(user_id: str, model: Type[U] = UserPrivate) -> Optional[U]:
    """Get user by ID from cache or Airtable."""
    return get_one("users", user_id, model=model)


def get_user_by_email(email: str, model: Type[U] = UserPrivate) -> Optional[U]:
    """Get user by email from cache or Airtable."""
    normalized_email = email.lower().strip()
    items = get_by_index("users", {"email": normalized_email}, model=model)
    return items[0] if items else None


def invalidate_user(user_id: str):
    """Remove user from cache (called by webhook or delete)."""
    invalidate_entity("users", user_id)


def upsert_user(user: UserPrivate):
    """Update or insert user in cache (called by webhook)."""
    upsert_entity("users", user)


def delete_user(user_id: str):
    """Delete user from Airtable and invalidate cache."""
    delete_entity("users", user_id)


# ===== VOTE OPERATIONS =====


def get_vote(vote_id: str) -> Optional[Vote]:
    """Get vote by ID from cache or Airtable."""
    return get_one("votes", vote_id, model=Vote)


def get_votes_for_event(event_id: str) -> List[Vote]:
    """Get all votes for an event using cache index."""
    return get_by_index("votes", {"event": event_id}, model=Vote)


def get_votes_for_project(project_id: str) -> List[Vote]:
    """Get all votes for a project using cache index."""
    return get_by_index("votes", {"project": project_id}, model=Vote)


def invalidate_vote(vote_id: str):
    """Remove vote from cache (called by webhook)."""
    invalidate_entity("votes", vote_id)


def upsert_vote(vote: Vote):
    """Update or insert vote in cache (called by webhook)."""
    upsert_entity("votes", vote)


def delete_vote(vote_id: str):
    """Delete vote from Airtable and invalidate cache."""
    delete_entity("votes", vote_id)


# ===== REFERRAL OPERATIONS =====


def get_referral(referral_id: str) -> Optional[Referral]:
    """Get referral by ID from cache or Airtable."""
    return get_one("referrals", referral_id, model=Referral)


def get_referrals_for_event(event_id: str) -> List[Referral]:
    """Get all referrals for an event using cache index."""
    return get_by_index("referrals", {"event": event_id}, model=Referral)


def invalidate_referral(referral_id: str):
    """Remove referral from cache (called by webhook)."""
    invalidate_entity("referrals", referral_id)


def upsert_referral(referral: Referral):
    """Update or insert referral in cache (called by webhook)."""
    upsert_entity("referrals", referral)


def delete_referral(referral_id: str):
    """Delete referral from Airtable and invalidate cache."""
    delete_entity("referrals", referral_id)
