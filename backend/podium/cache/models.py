"""Redis-OM JsonModel definitions for caching."""

from redis_om import JsonModel, Field as RedisField
from typing import Type
from pydantic import BaseModel, create_model

from podium.db.project import Project
from podium.db.event import Event, PrivateEvent
from podium.db.user import UserPrivate, UserPublic
from podium.db.vote import Vote
from podium.db.referral import Referral


def make_json_model(
    base_model: Type[BaseModel],
    indexed_fields: set[str] = None,
    sortable_fields: set[str] = None,
):
    """
    Dynamically create a redis-om JsonModel from a Pydantic BaseModel.
    
    Args:
        base_model: The Pydantic model to convert
        indexed_fields: Set of field names to create RediSearch indices for (TAG fields)
        sortable_fields: Set of field names that can be sorted (NUMERIC/TEXT fields)
        
    Returns:
        A JsonModel class with the same fields, plus indices on specified fields
        
    Note: TAG fields (for exact match) cannot be sortable in redis-om.
          Use indexed_fields for IDs/slugs, sortable_fields for numeric/text.
    """
    indexed_fields = indexed_fields or set()
    sortable_fields = sortable_fields or set()
    
    field_defs = {}
    for name, field_info in base_model.model_fields.items():
        annotation = field_info.annotation
        
        is_indexed = name in indexed_fields
        is_sortable = name in sortable_fields
        
        if is_indexed and is_sortable:
            # Both indexed and sortable (NUMERIC field only)
            field_defs[name] = (annotation, RedisField(index=True, sortable=True))
        elif is_indexed:    
            # Index only (TAG field for exact match - disable full-text tokenization)
            field_defs[name] = (annotation, RedisField(index=True, full_text_search=False))
        elif is_sortable:
            # Sortable only (for ordering without filtering)
            field_defs[name] = (annotation, RedisField(sortable=True))
        else:
            # Regular field (not queryable, only fetchable by primary key)
            field_defs[name] = (annotation, field_info)
    
    return create_model(
        f"{base_model.__name__}Cache",
        __base__=JsonModel,
        **field_defs
    )


# Create cache models with indexed fields for efficient querying
# indexed_fields: TAG fields for exact match queries (IDs, slugs, emails)
# sortable_fields: NUMERIC fields for sorting (points, etc.)
#
# Strategy: Cache only "Private" variants (full data), derive public views on read
# This eliminates dual-update issues and simplifies invalidation

ProjectCache = make_json_model(
    Project,
    indexed_fields={"event", "owner"},  # Query by event, owner (TAG fields)
    sortable_fields={"points"}  # Sort by points (NUMERIC field)
)

# Cache PrivateEvent only - derive Event (public) on read
EventCache = make_json_model(
    PrivateEvent,
    indexed_fields={"slug", "owner"}  # Query by slug, owner (TAG fields)
)

# Cache UserPrivate only - derive UserPublic on read
UserCache = make_json_model(
    UserPrivate,
    indexed_fields={"email"}  # Query by email (TAG field)
)

VoteCache = make_json_model(
    Vote,
    indexed_fields={"event", "project", "voter"}  # Query votes by event/project/voter (TAG fields)
)

ReferralCache = make_json_model(
    Referral,
    indexed_fields={"event"}  # Query referrals by event (TAG field)
)
