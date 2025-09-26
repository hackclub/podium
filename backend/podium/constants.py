from typing import Annotated, List
from annotated_types import Len
from fastapi import HTTPException
from pydantic import BaseModel, StringConstraints
from enum import Enum


RECORD_REGEX = r"^rec\w*$"
# URL_REGEX = r"^(https?://)?([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(:\d+)?(/[\w\-./?%&=]*)?$"
URL_REGEX = r"^(https?://)?([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(:\d+)?(/[\w\-./?%&=]*)?$"

# https://docs.pydantic.dev/latest/api/types/#pydantic.types.constr--__tabbed_1_2
MultiRecordField = List[Annotated[str, StringConstraints(pattern=RECORD_REGEX)]]
SingleRecordField = Annotated[
    List[Annotated[str, StringConstraints(pattern=RECORD_REGEX)]],
    Len(min_length=1, max_length=1),
]
# URL fields with regex validation
UrlField = Annotated[str, StringConstraints(min_length=1, pattern=URL_REGEX)]
OptionalUrlField = Annotated[str, StringConstraints(min_length=0, pattern=rf"^$|{URL_REGEX[1:-1]}")]

Slug = Annotated[
    str, StringConstraints(min_length=1, max_length=50, pattern=r"[-a-z0-9]+")
]

# raise\s+HTTPException\([^)]*["'].*User.*["']
BAD_AUTH = HTTPException(status_code=401, detail="Invalid authentication credentials")
BAD_ACCESS = HTTPException(
    status_code=403, detail="You don't have permission to do this"
)

AIRTABLE_NOT_FOUND_CODES = [404, 403]
class FeatureFlag(Enum):
    """Known feature flags - add new ones here as they're created."""
    DAYDREAM = "daydream"  # Daydream-specific features

# Comma-separated feature flags (e.g., "flag1,flag2"); regex ensures only alphanum/underscore names, no spaces.
# Empty string is allowed for no flags
CommaSeparatedFeatureFlags = Annotated[
    str,
    StringConstraints(pattern=r"^([a-zA-Z0-9_]+(,[a-zA-Z0-9_]+)*)?$")
]






class EmptyModel(BaseModel):
    pass
