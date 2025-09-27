from fastapi import HTTPException
from podium import db
from podium.constants import (
    AIRTABLE_NOT_FOUND_CODES,
    MultiRecordField,
    SingleRecordField,
    Slug,
    CommaSeparatedFeatureFlags,
    FeatureFlag,
)
from pydantic import BaseModel, StringConstraints, computed_field
from typing import Annotated, List, Optional, Type, TypeVar
from functools import cached_property
from pyairtable.formulas import OR, EQ, Field as AirtableField
from podium.db import tables

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
    feature_flags_csv: CommaSeparatedFeatureFlags = ""

    """In addition to the normal fields, we also have lookup fields in Airtable so we can use formulas:
    - owner_id
    """

    @computed_field
    @property
    def feature_flags_list(self) -> List[str]:
        """Get feature flags as a list, filtering out empty strings."""
        if not self.feature_flags_csv:
            return []
        return [
            flag.strip() for flag in self.feature_flags_csv.split(",") if flag.strip()
        ]

    def add_feature_flag(self, flag: str) -> str:
        """Add a feature flag and return the updated comma-separated string."""
        if not flag or not str(flag).strip():
            return self.feature_flags_csv

        flag_str = str(flag).strip()
        current_flags = self.feature_flags_list

        if flag_str not in current_flags:
            current_flags.append(flag_str)
            return ",".join(sorted(current_flags))

        return self.feature_flags_csv

    def remove_feature_flag(self, flag: str) -> str:
        """Remove a feature flag and return the updated comma-separated string."""
        if not flag:
            return self.feature_flags_csv

        flag_str = str(flag).strip()
        current_flags = self.feature_flags_list

        if flag_str in current_flags:
            current_flags.remove(flag_str)
            return ",".join(sorted(current_flags))

        return self.feature_flags_csv

    @classmethod
    def create_feature_flags_string(cls, flags: List[str]) -> str:
        """Create a comma-separated feature flags string from a list of flags."""
        if not flags:
            return ""

        # Filter out empty strings and strip whitespace
        valid_flags = [
            str(flag).strip() for flag in flags if flag and str(flag).strip()
        ]

        if not valid_flags:
            return ""

        # Remove duplicates and sort for consistency
        unique_flags = sorted(list(set(valid_flags)))
        return ",".join(unique_flags)

    @classmethod
    def get_known_feature_flags(cls) -> List[str]:
        """Get a list of all known feature flags for reference."""
        return [flag.value for flag in FeatureFlag]

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


class InternalEvent(PrivateEvent): ...


class UserEvents(BaseModel):
    """Return information regarding what the events the user owns and what events they are attending. If they are only attending an event, don't return sensitive information like participants."""

    owned_events: List[PrivateEvent]
    # This was just the creation payload earlier and I was wondering why the ID wasn't being returned...
    attending_events: List[Event]


T = TypeVar("T", bound=BaseEvent)


def get_events_from_record_ids(record_ids: List[str], model: Type[T]) -> List[T]:
    events_table = tables["events"]
    if not record_ids:
        return []

    # Use PyAirtable's OR and EQ functions for multiple record ID matching
    expressions = [EQ(AirtableField("id"), record_id) for record_id in record_ids]
    formula = OR(*expressions)

    records = events_table.all(formula=formula)
    return [model.model_validate(record["fields"]) for record in records]
