"""
Event model and API schemas.

An Event is a hackathon where users submit projects and vote.
"""

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from pydantic import computed_field, field_validator
from sqlmodel import Field, SQLModel, Relationship

from podium.constants import EventPhase
from podium.db.postgres.links import EventAttendeeLink

if TYPE_CHECKING:
    from podium.db.postgres.user import User
    from podium.db.postgres.project import Project
    from podium.db.postgres.vote import Vote
    from podium.db.postgres.referral import Referral


class Event(SQLModel, table=True):
    """Hackathon event - maps to 'events' table."""

    __tablename__: str = "events"

    # Primary key - auto-generated UUID
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Core fields
    name: str = Field(max_length=255)
    slug: str = Field(max_length=50, unique=True, index=True)
    description: str = Field(default="")

    # Event lifecycle phase — controls what actions are allowed (see EventPhase enum)
    phase: str = Field(default=EventPhase.DRAFT, max_length=20)

    # Feature flags
    demo_links_optional: bool = Field(default=False)
    ysws_checks_enabled: bool = Field(default=False)
    feature_flags_csv: str = Field(default="", max_length=500)

    # Owner (foreign key to users)
    owner_id: UUID = Field(foreign_key="users.id")

    # Relationships
    owner: "User" = Relationship(back_populates="owned_events")
    attendees: list["User"] = Relationship(
        back_populates="events_attending", link_model=EventAttendeeLink
    )
    projects: list["Project"] = Relationship(back_populates="event")
    votes: list["Vote"] = Relationship(back_populates="event")
    referrals: list["Referral"] = Relationship(back_populates="event")

    @field_validator("phase")
    @classmethod
    def validate_phase(cls, v: str) -> str:
        valid = {p.value for p in EventPhase}
        if v not in valid:
            raise ValueError(f"phase must be one of {valid}")
        return v

    @computed_field
    @property
    def feature_flags_list(self) -> list[str]:
        """Parse comma-separated feature flags into a list."""
        if not self.feature_flags_csv:
            return []
        return [f.strip() for f in self.feature_flags_csv.split(",") if f.strip()]

    @computed_field
    @property
    def max_votes_per_user(self) -> int:
        """Calculate max votes based on project count (matches original Airtable logic)."""
        project_count = len(self.projects) if self.projects else 0
        if project_count < 4:
            return 1
        elif project_count < 20:
            return 2
        else:
            return 3



# =============================================================================
# API SCHEMAS
# =============================================================================


class EventPublic(SQLModel):
    """Public event info - visible to anyone."""

    id: UUID
    name: str
    slug: str
    description: str
    phase: str
    demo_links_optional: bool
    max_votes_per_user: int


class EventPrivate(EventPublic):
    """Private event info - visible to owner and attendees."""

    owner_id: UUID
    ysws_checks_enabled: bool


class EventUpdate(SQLModel):
    """Request body for updating an event. All fields optional."""

    name: str | None = None
    description: str | None = None
    phase: str | None = None
    demo_links_optional: bool | None = None
    ysws_checks_enabled: bool | None = None
