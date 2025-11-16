"""
Simplified caching layer for Podium.

Zero-touch: adding/changing models requires NO cache code changes.

Usage:
    from podium import cache
    from podium.cache.operations import Entity

    # Get by ID (use Entity enum for type safety)
    event = cache.get_one(Entity.EVENTS, id, Event)
    user = cache.get_one(Entity.USERS, id, UserPrivate)

    # Get by field (uses Airtable query, caches result)
    user = cache.get_by_formula(Entity.USERS, {"email": "user@example.com"}, UserPrivate)
    event = cache.get_by_formula(Entity.EVENTS, {"slug": "my-event"}, Event)

    # Get multiple
    events = cache.get_many_by_ids(Entity.EVENTS, [id1, id2], Event)
    projects = cache.get_many_by_formula(Entity.PROJECTS, {"event_id": event_id}, Project)

    # Add new entity (zero cache changes needed)
    comment = cache.get_one(Entity.COMMENTS, id, Comment)  # Add COMMENTS to Entity enum
"""

from podium.cache.client import get_redis_client
from podium.cache.operations import (
    Entity,
    delete_entity,
    get_by_formula,
    get_many_by_formula,
    get_many_by_ids,
    get_one,
    get_user_by_email,
    put_user_in_cache,
    invalidate_entity,
    upsert_entity,
)

__all__ = [
    "get_redis_client",
    # Entity enum
    "Entity",
    # Core API
    "get_one",
    "get_many_by_ids",
    "get_by_formula",
    "get_many_by_formula",
    "get_user_by_email",
    "put_user_in_cache",
    "upsert_entity",
    "invalidate_entity",
    "delete_entity",
]
