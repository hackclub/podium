from podium.constants import SingleRecordField
from pydantic import BaseModel

class VoteBase(BaseModel):
    project: str
    event: SingleRecordField

class Vote(VoteBase):
    id: str
    voter: SingleRecordField