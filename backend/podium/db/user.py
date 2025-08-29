import datetime
from typing import Annotated, List, Optional, Type, TypeVar
from pydantic import BaseModel, Field, StringConstraints
from podium import constants

from podium.db import tables
from pyairtable.formulas import match

FirstName = Annotated[str, Field(..., min_length=1, max_length=50)]
LastName = Annotated[str, Field(default="")]
EmailStrippedLower = Annotated[
    str, StringConstraints(strip_whitespace=True, to_lower=True)
]


class UserLoginPayload(BaseModel):
    email: EmailStrippedLower


class UserBase(BaseModel):
    display_name: str = ""

class UserPublic(UserBase): ...

class UserAttendee(UserPublic): 
    email: EmailStrippedLower
    first_name: FirstName
    last_name: LastName



class UserSignupPayload(UserAttendee):
    # Optional since some users don't have a last name in the DB
    # International phone number format, allowing empty string
    # this should have a default since I think Airtable may return None
    phone: Annotated[str, StringConstraints(pattern=r"(^$|^\+?[\d\-\(\)\s]{7,20}$)")] = ""
    street_1: Optional[str] = ""
    street_2: Optional[str] = ""
    city: Optional[str] = ""
    state: Optional[str] = ""
    # str but only allow digits
    zip_code: Optional[Annotated[str, StringConstraints(pattern=r"^.*$")]] = ""
    # https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2
    # country: Optional[Annotated[str, StringConstraints(pattern=r"(^$|^[A-Z]{2}$)")]] = ""
    # I think some other HQ stuff uses the full country name
    country: Optional[Annotated[str, StringConstraints(pattern=r"(^$|^[\w\s]+$)")]] = ""
    # YYYY-MM-DD or unix time is probably the best
    # Airtable returns 2025-01-25 :)
    dob: Optional[datetime.date] = None

    def model_dump(self, *args, **kwargs):
        data = super().model_dump(*args, **kwargs)
        # Convert dob to YYYY-MM-DD
        if isinstance(self.dob, datetime.date):
            data["dob"] = self.dob.strftime("%Y-%m-%d")
        else:
            data["dob"] = None
        return data

    # Ensure email is normalized to lowercase and stripped of whitespace
    # @field_validator("email", mode="before")
    # def normalize_email(cls, v: str) -> str:
    #     return v.strip().lower()


class UserUpdate(UserSignupPayload): ...

class UserPrivate(UserSignupPayload): 
    id: Annotated[str, StringConstraints(pattern=constants.RECORD_REGEX)]
    votes: constants.MultiRecordField = []
    projects: constants.MultiRecordField = []
    collaborations: constants.MultiRecordField = []
    owned_events: constants.MultiRecordField = []
    attending_events: constants.MultiRecordField = []
    referral: constants.MultiRecordField = []

class UserInternal(UserPrivate): ...



def get_user_record_id_by_email(email: str) -> Optional[str]:
    users_table = tables["users"]
    formula = match({"email": email})
    records = users_table.all(formula=formula)
    return records[0]["id"] if records else None


T = TypeVar("T", bound=UserBase)
def get_users_from_record_ids(record_ids: List[str], model: Type[T]) -> List[T]:
    users_table = tables["users"]
    records = users_table.batch_get(record_ids)
    return [model.model_validate(record["fields"]) for record in records]