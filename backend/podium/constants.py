from typing import Annotated, List
from annotated_types import Len
from fastapi import HTTPException
from pydantic import BaseModel, StringConstraints


RECORD_REGEX = r"^rec\w*$"
URL_REGEX = r"^(https?://)?([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(:\d+)?(/[\w\-./?%&=]*)?$"

# https://docs.pydantic.dev/latest/api/types/#pydantic.types.constr--__tabbed_1_2
MultiRecordField = List[Annotated[str, StringConstraints(pattern=RECORD_REGEX)]]
SingleRecordField = Annotated[
    List[Annotated[str, StringConstraints(pattern=RECORD_REGEX)]],
    Len(min_length=1, max_length=1),
]
UrlField = Annotated[
    str, StringConstraints(pattern=URL_REGEX, min_length=1)
]


# raise\s+HTTPException\([^)]*["'].*User.*["']
BAD_AUTH = HTTPException(status_code=401, detail="Invalid authentication credentials")
BAD_ACCESS = HTTPException(
    status_code=403, detail="You don't have permission to do this"
)

AIRTABLE_NOT_FOUND_CODES = [404, 403]


class EmptyModel(BaseModel):
    pass
