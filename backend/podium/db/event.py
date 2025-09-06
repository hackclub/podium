from fastapi import HTTPException
from podium import db
from podium.constants import AIRTABLE_NOT_FOUND_CODES, MultiRecordField, SingleRecordField, Slug
from pydantic import BaseModel, StringConstraints, computed_field
from typing import Annotated, List, Optional
from functools import cached_property

from requests import HTTPError


# https://docs.pydantic.dev/1.10/usage/schema/#field-customization
class BaseEvent(BaseModel):
    name: Annotated[str, StringConstraints(min_length=1)]
    description: Optional[Annotated[str, StringConstraints(max_length=500)]] = ""
    votable: bool = False
    leaderboard_enabled: bool = False
    demo_links_optional: bool = False


class EventCreationPayload(BaseEvent): ...


class EventUpdate(BaseEvent): ...


class Event(EventCreationPayload):
    id: str
    owner: SingleRecordField
    slug: Slug  # Slug is auto-generated

    # feature flags
    # Should the user see their project as valid or invalid depending on the automatic checks?
    ysws_checks_enabled: bool = False

    @computed_field
    @cached_property
    def max_votes_per_user(self) -> int:
        try:
            event = db.events.get(self.id)
        except HTTPError as e:
            raise (
            HTTPException(status_code=404, detail="Event not found")
            if e.response.status_code in AIRTABLE_NOT_FOUND_CODES
            else e
        )
        event = InternalEvent.model_validate(event["fields"])

        if len(event.projects) >= 20:
            return 3
        elif len(event.projects) >= 4:
            return 2
        else:
            return 1



class PrivateEvent(Event):
    """
    All data loaded from the event table. Should only be used internally or by the owner of the event.
    """

    # https://stackoverflow.com/questions/63793662/how-to-give-a-pydantic-list-field-a-default-value/63808835#63808835
    # List of record IDs, since that's what Airtable uses
    attendees: MultiRecordField = []
    join_code: str
    projects: MultiRecordField = []
    referrals: MultiRecordField = []
    # If the frontend has a PrivateEvent object, it means the user has owner access to the event
    owned: Optional[bool] = True



# TODO: Migrate internal uses of PrivateEvent to InternalEvent
class InternalEvent(PrivateEvent): ...


class UserEvents(BaseModel):
    """Return information regarding what the events the user owns and what events they are attending. If they are only attending an event, don't return sensitive information like participants."""

    owned_events: List[PrivateEvent]
    # This was just the creation payload earlier and I was wondering why the ID wasn't being returned...
    attending_events: List[Event]
