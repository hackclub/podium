import datetime
from typing import Annotated, Optional
from pydantic import BaseModel, EmailStr, Field, StringConstraints
from podium import constants

from podium.db import tables
from pyairtable.formulas import match


class UserBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50)
    # Optional since some users don't have a last name in the DB
    last_name: str = "N/A"
    email: EmailStr
    # International phone number format, allowing empty string
    # this should have a default since I think Airtable may return None 
    phone: Annotated[str, StringConstraints(pattern=r"(^$|^\+?[1-9]\d{1,14}$)")] = ""
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


class UserSignupPayload(UserBase): ...


class User(UserBase):
    id: Annotated[str, StringConstraints(pattern=constants.RECORD_REGEX)]
    votes: constants.MultiRecordField = []
    projects: constants.MultiRecordField = []
    owned_events: constants.MultiRecordField = []
    attending_events: constants.MultiRecordField = []
    referral: constants.MultiRecordField = []


class CurrentUser(BaseModel):
    email: str


# TODO: make this part of CurrentUser or something, since this is used way too much
def get_user_record_id_by_email(email: str) -> Optional[str]:
    users_table = tables["users"]
    formula = match({"email": email})
    records = users_table.all(formula=formula)
    return records[0]["id"] if records else None
