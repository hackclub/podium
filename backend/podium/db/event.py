from podium.constants import MultiRecordField, SingleRecordField
from pydantic import BaseModel, StringConstraints, computed_field
from typing import Annotated, List, Optional


# https://docs.pydantic.dev/1.10/usage/schema/#field-customization
class BaseEvent(BaseModel):
    name: Annotated[str, StringConstraints(min_length=1)]
    description: Optional[Annotated[str, StringConstraints(max_length=500)]] = ""
    votable: bool = False


class EventCreationPayload(BaseEvent): ...


class EventUpdate(BaseEvent): ...
    

class Event(EventCreationPayload):
    id: str
    owner: SingleRecordField


class PrivateEvent(Event):
    # https://stackoverflow.com/questions/63793662/how-to-give-a-pydantic-list-field-a-default-value/63808835#63808835
    # List of record IDs, since that's what Airtable uses
    attendees: MultiRecordField = []
    join_code: str
    projects: MultiRecordField = []
    referrals: MultiRecordField = []
    
    @computed_field
    @property
    def max_votes_per_user(self) -> int:
        """
        The maximum number of votes a user can cast for this event. This is based on the number of projects in the event. If there are 20 or more projects, the user can vote for 3 projects. Otherwise, they can vote for 2 projects.
        """
        if len(self.projects) >= 20:
            return 3
        else:
            return 2
        


class UserEvents(BaseModel):
    """Return information regarding what the events the user owns and what events they are attending. If they are only attending an event, don't return sensitive information like participants."""

    owned_events: List[PrivateEvent]
    # This was just the creation payload earlier and I was wondering why the ID wasn't being returned...
    attending_events: List[Event]
