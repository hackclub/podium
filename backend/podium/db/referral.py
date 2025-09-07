from pydantic import BaseModel
from podium.constants import SingleRecordField


class ReferralBase(BaseModel):
    content: str = ""
    event: SingleRecordField
    user: SingleRecordField


class Referral(ReferralBase):
    id: str
    # Note: Airtable also has this ID field for querying:
    # - event_id: Used in match formulas for event-based referral queries