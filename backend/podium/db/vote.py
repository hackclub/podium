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


class CreateVotes(BaseModel):
    projects: MultiRecordField
    event: Annotated[str, StringConstraints(pattern=RECORD_REGEX)]
