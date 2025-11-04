"""Redis-OM JsonModel definitions for caching."""

from redis_om import JsonModel, Field as RedisField, get_redis_connection
from typing import Type
from pydantic import BaseModel
from podium.db.project import Project
from podium.db.event import PrivateEvent
from podium.db.user import UserPrivate
from podium.db.vote import Vote
from podium.db.referral import Referral
from podium.config import settings

# Get shared Redis connection for all models
_redis_conn = get_redis_connection(url=settings.redis_url, decode_responses=False)


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
    
    # Build field definitions with proper redis-om Field descriptors
    class_dict = {'__annotations__': {}}
    
    for name, field_info in base_model.model_fields.items():
        annotation = field_info.annotation
        class_dict['__annotations__'][name] = annotation
        
        is_indexed = name in indexed_fields
        is_sortable = name in sortable_fields
        
        if is_indexed and is_sortable:
            # Both indexed and sortable (NUMERIC field only)
            class_dict[name] = RedisField(index=True, sortable=True)
        elif is_indexed:    
            # Index only (TAG field for exact match)
            class_dict[name] = RedisField(index=True, full_text_search=False)
        elif is_sortable:
            # Sortable only (for ordering without filtering)
            class_dict[name] = RedisField(sortable=True)
    
    # Create Meta class with Redis connection
    class Meta:
        database = _redis_conn
    
    class_dict['Meta'] = Meta
    
    # Create the model class
    model_class = type(
        f"{base_model.__name__}Cache",
        (JsonModel,),
        class_dict
    )
    
    return model_class


# Create cache models with indexed fields for efficient querying
# indexed_fields: TAG fields for exact match queries (IDs, slugs, emails)
# sortable_fields: NUMERIC fields for sorting (points, etc.)
#
# Strategy: Cache only "Private" variants (full data), derive public views on read

ProjectCache = make_json_model(
    Project,
    indexed_fields={"event", "owner"},
    sortable_fields={"points"}
)

EventCache = make_json_model(
    PrivateEvent,
    indexed_fields={"slug", "owner"}
)

UserCache = make_json_model(
    UserPrivate,
    indexed_fields={"email"}
)

VoteCache = make_json_model(
    Vote,
    indexed_fields={"event", "project", "voter"}
)

ReferralCache = make_json_model(
    Referral,
    indexed_fields={"event"}
)
