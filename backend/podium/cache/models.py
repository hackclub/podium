"""Redis-OM JsonModel definitions for caching."""

from redis_om import JsonModel, Field as RedisField, get_redis_connection
from typing import Type
from pydantic import BaseModel
from podium.cache.auto_config import auto_detect_cache_config
from podium.db.project import Project, PrivateProject
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


# Create cache models with auto-detected indexed fields
# Strategy: Cache only "Private" variants (full data), derive public views on read

# Auto-detect configurations
_project_config = auto_detect_cache_config(PrivateProject)
_event_config = auto_detect_cache_config(PrivateEvent)
_user_config = auto_detect_cache_config(UserPrivate)
_vote_config = auto_detect_cache_config(Vote)
_referral_config = auto_detect_cache_config(Referral)

ProjectCache = make_json_model(
    Project,
    indexed_fields=_project_config["indexed_fields"],
    sortable_fields=_project_config["sortable_fields"]
)

EventCache = make_json_model(
    PrivateEvent,
    indexed_fields=_event_config["indexed_fields"],
    sortable_fields=_event_config["sortable_fields"]
)

UserCache = make_json_model(
    UserPrivate,
    indexed_fields=_user_config["indexed_fields"],
    sortable_fields=_user_config["sortable_fields"]
)

VoteCache = make_json_model(
    Vote,
    indexed_fields=_vote_config["indexed_fields"],
    sortable_fields=_vote_config["sortable_fields"]
)

ReferralCache = make_json_model(
    Referral,
    indexed_fields=_referral_config["indexed_fields"],
    sortable_fields=_referral_config["sortable_fields"]
)
