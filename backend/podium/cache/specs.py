"""Entity specifications for generic cache operations."""

from dataclasses import dataclass
from typing import Callable, Dict, Optional, Type

from pydantic import BaseModel
from redis_om import JsonModel

from podium.cache.models import (
    EventCache,
    ProjectCache,
    ReferralCache,
    UserCache,
    VoteCache,
)
from podium.db.event import Event, PrivateEvent
from podium.db.project import Project
from podium.db.referral import Referral
from podium.db.user import UserPrivate, UserPublic
from podium.db.vote import Vote


@dataclass(frozen=True)
class EntitySpec:
    """Specification for a cacheable entity."""

    name: str  # Entity name (e.g., "projects")
    table: str  # Airtable table name
    cache_model: Type[JsonModel]  # redis-om JsonModel
    cache_pydantic: Type[BaseModel]  # Richest model we cache (e.g., PrivateEvent)
    default_read_model: Type[BaseModel]  # Default public model to return
    index_to_airtable: Dict[str, str] | None = None  # Map cache field -> Airtable field
    normalize_before_cache: Optional[Callable[[dict], dict]] = None  # Optional hook


def _normalize_user(data: dict) -> dict:
    """Normalize user data before caching (lowercase email)."""
    if "email" in data and data["email"]:
        data["email"] = data["email"].lower().strip()
    return data


def _normalize_vote(data: dict) -> dict:
    """Flatten SingleRecordField lists to strings for indexing."""
    for field in ["event", "project", "voter"]:
        if field in data and isinstance(data[field], list) and len(data[field]) > 0:
            data[field] = data[field][0]
    return data


def _normalize_referral(data: dict) -> dict:
    """Flatten SingleRecordField lists to strings for indexing."""
    for field in ["event", "user"]:
        if field in data and isinstance(data[field], list) and len(data[field]) > 0:
            data[field] = data[field][0]
    return data


def _normalize_project(data: dict) -> dict:
    """Flatten SingleRecordField lists to strings for indexing."""
    # event and owner are SingleRecordFields that need flattening for index queries
    for field in ["event", "owner"]:
        if field in data and isinstance(data[field], list) and len(data[field]) > 0:
            data[field] = data[field][0]
    return data


def _normalize_event(data: dict) -> dict:
    """Flatten SingleRecordField lists to strings for indexing."""
    # owner is SingleRecordField that needs flattening for index queries
    if "owner" in data and isinstance(data["owner"], list) and len(data["owner"]) > 0:
        data["owner"] = data["owner"][0]
    return data


# Entity registry: all cacheable entities
ENTITIES: Dict[str, EntitySpec] = {
    "projects": EntitySpec(
        name="projects",
        table="projects",
        cache_model=ProjectCache,
        cache_pydantic=Project,
        default_read_model=Project,
        index_to_airtable={"event": "event_id"},  # Airtable uses flattened lookup
        normalize_before_cache=_normalize_project,
    ),
    "events": EntitySpec(
        name="events",
        table="events",
        cache_model=EventCache,
        cache_pydantic=PrivateEvent,  # Cache the richest model
        default_read_model=Event,  # Default to public view
        index_to_airtable={"slug": "slug", "owner": "owner_id"},  # Airtable uses flattened lookup
        normalize_before_cache=_normalize_event,
    ),
    "users": EntitySpec(
        name="users",
        table="users",
        cache_model=UserCache,
        cache_pydantic=UserPrivate,  # Cache the richest model
        default_read_model=UserPublic,  # Default to public view
        index_to_airtable={"email": "email"},
        normalize_before_cache=_normalize_user,
    ),
    "votes": EntitySpec(
        name="votes",
        table="votes",
        cache_model=VoteCache,
        cache_pydantic=Vote,
        default_read_model=Vote,
        index_to_airtable={"event": "event_id", "project": "project_id", "voter": "user_id"},
        normalize_before_cache=_normalize_vote,
    ),
    "referrals": EntitySpec(
        name="referrals",
        table="referrals",
        cache_model=ReferralCache,
        cache_pydantic=Referral,
        default_read_model=Referral,
        index_to_airtable={"event": "event_id"},  # Airtable uses flattened lookup
        normalize_before_cache=_normalize_referral,
    ),
}
