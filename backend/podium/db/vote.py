from typing import Annotated
from podium.constants import RECORD_REGEX, MultiRecordField, SingleRecordField
from pydantic import BaseModel, StringConstraints


class VoteBase(BaseModel):
    project: SingleRecordField
    event: SingleRecordField
    voter: SingleRecordField


class VoteCreate(VoteBase): ...


class Vote(VoteCreate):
    id: str
    # Note: Airtable also has these ID fields for querying:
    # - user_id: Used in match formulas for voter lookups
    # - event_id: Used in match formulas for event-based queries
    # - project_id: Used in match formulas for project-specific vote queries


class CreateVotes(BaseModel):
    projects: MultiRecordField
    event: Annotated[str, StringConstraints(pattern=RECORD_REGEX)]
