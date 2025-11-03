"""
Valkey/Redis caching layer for Podium.

Provides cache-aside pattern with automatic invalidation via Airtable webhooks.

IMPORTANT: All deletes must go through delete_* functions (not direct Airtable access).
This ensures cache invalidation and tombstone marking.
"""

from .client import get_redis_client
from .operations import (
    # Read operations
    get_project,
    get_projects_for_event,
    get_event,
    get_event_by_slug,
    get_user,
    get_user_by_email,
    get_vote,
    # Delete operations (use these instead of db.*.delete())
    delete_event,
    delete_project,
    delete_user,
    delete_vote,
    delete_referral,
    # Manual invalidation (for special cases)
    invalidate_project,
    invalidate_event,
    invalidate_user,
    invalidate_vote,
)

__all__ = [
    "get_redis_client",
    # Reads
    "get_project",
    "get_projects_for_event",
    "get_event",
    "get_event_by_slug",
    "get_user",
    "get_user_by_email",
    "get_vote",
    # Deletes (ALWAYS use these)
    "delete_event",
    "delete_project",
    "delete_user",
    "delete_vote",
    "delete_referral",
    # Manual invalidation
    "invalidate_project",
    "invalidate_event",
    "invalidate_user",
    "invalidate_vote",
]
