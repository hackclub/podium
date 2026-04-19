"""
Event model and API schemas.

An Event is a hackathon where users submit projects and vote.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from pydantic import computed_field, field_validator
from sqlmodel import Field, SQLModel, Relationship

from podium.constants import EventPhase, RepoValidation, DemoValidation
from podium.db.postgres.links import EventAttendeeLink

if TYPE_CHECKING:
    from podium.db.postgres.user import User
    from podium.db.postgres.project import Project
    from podium.db.postgres.vote import Vote
    from podium.db.postgres.referral import Referral


class Event(SQLModel, table=True):
    """Hackathon event — maps to 'events' table."""

    __tablename__: str = "events"

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    name: str = Field(max_length=255)
    slug: str = Field(max_length=50, unique=True, index=True)
    description: str = Field(default="")

    # Lifecycle phase — controls what actions are allowed (see EventPhase enum)
    phase: str = Field(default=EventPhase.DRAFT, max_length=20)

    # Submission settings
    demo_links_optional: bool = Field(default=False)

    # Validation config — controls background validation per field
    repo_validation: str = Field(default=RepoValidation.GITHUB, max_length=20)
    demo_validation: str = Field(default=DemoValidation.NONE, max_length=20)
    # Names an entry in validators/custom/REGISTRY; only relevant when
    # repo_validation or demo_validation is set to "custom".
    custom_validator: str | None = Field(default=None, max_length=50)

    # Comma-separated feature flags (e.g. "flagship,sleepover")
    feature_flags_csv: str = Field(default="", max_length=500)

    owner_id: UUID = Field(foreign_key="users.id")

    # Require attendees to have a shipping address on file before submitting a project
    require_address: bool = Field(default=False)

    # Soft-delete — NULL means active; set to a timestamp to hide the event.
    deleted_at: datetime | None = Field(default=None)

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

    @field_validator("repo_validation")
    @classmethod
    def validate_repo_validation(cls, v: str) -> str:
        valid = {r.value for r in RepoValidation}
        if v not in valid:
            raise ValueError(f"repo_validation must be one of {valid}")
        return v

    @field_validator("demo_validation")
    @classmethod
    def validate_demo_validation(cls, v: str) -> str:
        valid = {d.value for d in DemoValidation}
        if v not in valid:
            raise ValueError(f"demo_validation must be one of {valid}")
        return v

    @computed_field
    @property
    def feature_flags_list(self) -> list[str]:
        if not self.feature_flags_csv:
            return []
        return [f.strip() for f in self.feature_flags_csv.split(",") if f.strip()]

    @computed_field
    @property
    def max_votes_per_user(self) -> int:
        """Votes allowed per user, scaled to project count."""
        count = len(self.projects) if self.projects else 0
        if count < 4:
            return 1
        if count < 20:
            return 2
        return 3

    @computed_field
    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


# =============================================================================
# API SCHEMAS
# =============================================================================


class EventPublic(SQLModel):
    """Public event info — visible to anyone."""

    id: UUID
    name: str
    slug: str
    description: str
    phase: str
    demo_links_optional: bool
    require_address: bool
    max_votes_per_user: int
    # Expose validation config so the frontend can drive instant warnings
    repo_validation: str
    demo_validation: str


class EventPrivate(EventPublic):
    """Extended event info — visible to owner and superadmins."""

    owner_id: UUID
    custom_validator: str | None
    deleted_at: datetime | None = None


class EventUpdate(SQLModel):
    """Request body for updating an event (PATCH semantics — all fields optional)."""

    name: str | None = None
    description: str | None = None
    phase: str | None = None
    demo_links_optional: bool | None = None
    require_address: bool | None = None
    repo_validation: str | None = None
    demo_validation: str | None = None
    custom_validator: str | None = None
    feature_flags_csv: str | None = None
