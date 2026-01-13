"""
User model and API schemas.

Table model (User) maps to the database.
Schema models (UserPublic, UserPrivate, etc.) are for API responses/requests.
"""

from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel, Relationship

from podium.db.postgres.links import EventAttendeeLink, ProjectCollaboratorLink

if TYPE_CHECKING:
    from podium.db.postgres.event import Event
    from podium.db.postgres.project import Project
    from podium.db.postgres.vote import Vote
    from podium.db.postgres.referral import Referral


class User(SQLModel, table=True):
    """User account - maps to 'users' table."""

    __tablename__: str = "users"

    # Primary key - auto-generated UUID
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Core fields
    email: str = Field(max_length=255, unique=True, index=True)
    display_name: str = Field(default="", max_length=255)
    first_name: str = Field(max_length=50)
    last_name: str = Field(default="", max_length=50)
    phone: str = Field(default="", max_length=20)

    # Address fields
    street_1: str = Field(default="", max_length=255)
    street_2: str = Field(default="", max_length=255)
    city: str = Field(default="", max_length=100)
    state: str = Field(default="", max_length=100)
    zip_code: str = Field(default="", max_length=20)
    country: str = Field(default="", max_length=100)
    dob: date | None = Field(default=None)

    # Relationships: things this user owns
    owned_events: list["Event"] = Relationship(back_populates="owner")
    owned_projects: list["Project"] = Relationship(back_populates="owner")
    votes: list["Vote"] = Relationship(back_populates="voter")
    referrals: list["Referral"] = Relationship(back_populates="user")

    # Many-to-many: events attending and projects collaborating on
    events_attending: list["Event"] = Relationship(
        back_populates="attendees", link_model=EventAttendeeLink
    )
    projects_collaborating: list["Project"] = Relationship(
        back_populates="collaborators", link_model=ProjectCollaboratorLink
    )

    # DEPRECATED: For migration from Airtable only. Remove after migration.
    airtable_id: str | None = Field(default=None, max_length=32, unique=True, index=True)


# =============================================================================
# API SCHEMAS (not database tables - used for request/response validation)
# =============================================================================


class UserPublic(SQLModel):
    """Public user info - visible to anyone."""

    id: UUID
    display_name: str


class UserPrivate(UserPublic):
    """Private user info - visible to the user themselves and event owners."""

    email: str
    first_name: str
    last_name: str
    phone: str = ""


class UserSignup(SQLModel):
    """Request body for user signup."""

    email: str
    first_name: str
    last_name: str | None = ""
    display_name: str | None = ""
    phone: str | None = ""
    street_1: str | None = ""
    street_2: str | None = ""
    city: str | None = ""
    state: str | None = ""
    zip_code: str | None = ""
    country: str | None = ""
    dob: date | None = None


class UserUpdate(SQLModel):
    """Request body for updating user profile. All fields optional."""

    display_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    street_1: str | None = None
    street_2: str | None = None
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None
    country: str | None = None
    dob: date | None = None
