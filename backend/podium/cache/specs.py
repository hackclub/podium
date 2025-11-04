"""Entity specifications for generic cache operations."""

from dataclasses import dataclass
from typing import Callable, Dict, Optional, Type

from pydantic import BaseModel
from redis_om import JsonModel

from podium.cache.auto_config import auto_detect_cache_config
from podium.cache.models import (
    EventCache,
    ProjectCache,
    ReferralCache,
    UserCache,
    VoteCache,
)
from podium.db.event import Event, PrivateEvent
from podium.db.project import Project, PrivateProject
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


# Auto-detect cache configurations for each entity
_project_config = auto_detect_cache_config(PrivateProject)
_event_config = auto_detect_cache_config(PrivateEvent)
_user_config = auto_detect_cache_config(UserPrivate)
_vote_config = auto_detect_cache_config(Vote)
_referral_config = auto_detect_cache_config(Referral)

# Compose user normalization with auto-normalization
def _normalize_user_composed(data: dict) -> dict:
    data = _normalize_user(data)  # Email lowercasing
    data = _user_config["normalize_fn"](data)  # Auto-normalize SingleRecordFields
    return data

# Entity registry: all cacheable entities
ENTITIES: Dict[str, EntitySpec] = {
    "projects": EntitySpec(
        name="projects",
        table="projects",
        cache_model=ProjectCache,
        cache_pydantic=PrivateProject,
        default_read_model=Project,
        index_to_airtable=_project_config["index_to_airtable"],
        normalize_before_cache=_project_config["normalize_fn"],
    ),
    "events": EntitySpec(
        name="events",
        table="events",
        cache_model=EventCache,
        cache_pydantic=PrivateEvent,
        default_read_model=Event,
        index_to_airtable=_event_config["index_to_airtable"],
        normalize_before_cache=_event_config["normalize_fn"],
    ),
    "users": EntitySpec(
        name="users",
        table="users",
        cache_model=UserCache,
        cache_pydantic=UserPrivate,
        default_read_model=UserPublic,
        index_to_airtable=_user_config["index_to_airtable"],
        normalize_before_cache=_normalize_user_composed,
    ),
    "votes": EntitySpec(
        name="votes",
        table="votes",
        cache_model=VoteCache,
        cache_pydantic=Vote,
        default_read_model=Vote,
        index_to_airtable=_vote_config["index_to_airtable"],
        normalize_before_cache=_vote_config["normalize_fn"],
    ),
    "referrals": EntitySpec(
        name="referrals",
        table="referrals",
        cache_model=ReferralCache,
        cache_pydantic=Referral,
        default_read_model=Referral,
        index_to_airtable=_referral_config["index_to_airtable"],
        normalize_before_cache=_referral_config["normalize_fn"],
    ),
}
