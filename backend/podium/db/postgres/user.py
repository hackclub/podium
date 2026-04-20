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

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Core identity fields
    email: str = Field(max_length=255, unique=True, index=True)
    display_name: str = Field(default="", max_length=255)
    first_name: str = Field(max_length=50)
    last_name: str = Field(default="", max_length=50)
    phone: str = Field(default="", max_length=20)

    # Elevated access — superadmins can manage all events and set validation config
    is_superadmin: bool = Field(default=False)

    # Sensitive PII — must only appear in UserInternal, never in client-facing schemas.
    # If you add a new field here, do NOT add it to UserPublic or UserPrivate.
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


# =============================================================================
# API SCHEMAS (not database tables — used for request/response validation)
# =============================================================================


# ─── Mixin: sensitive PII address block ──────────────────────────────────────

class _AddressFields(SQLModel):
    """Address/PII fields used in response and write schemas.
    Only for truly internal/server-side use — not exposed to event admins or the client."""
    street_1: str = ""
    street_2: str = ""
    city: str = ""
    state: str = ""
    zip_code: str = ""
    country: str = ""
    dob: date | None = None


# ─── Read schemas (API responses) ────────────────────────────────────────────

class UserPublic(SQLModel):
    """Public user info — visible to anyone."""
    id: UUID
    display_name: str


class UserPrivate(UserPublic):
    """Authenticated user's self-view — returned by /users/current and /verify.
    Non-sensitive identity fields only. Address/DOB not included (see UserInternal)."""
    email: str
    first_name: str
    last_name: str
    phone: str = ""
    vote_ids: list[UUID] = []
    has_ysws_pii: bool = False
    is_superadmin: bool = False


class UserInternal(UserPrivate, _AddressFields):
    """Full user record including sensitive PII (address, DOB).
    Server-side/ops use only — never return to any client, including event admins."""
    pass


def has_ysws_pii(user: "User") -> bool:
    """YSWS prize eligibility: requires address (street, city, country) and DOB."""
    return bool(user.street_1 and user.city and user.country and user.dob)


def user_to_private(user: "User") -> "UserPrivate":
    """Build UserPrivate from a User model, extracting vote IDs from the loaded relationship.
    Requires User.votes to be loaded (via selectinload or similar).
    Raises ValueError if the relationship was not loaded (votes is None)."""
    if user.votes is None:
        raise ValueError("user_to_private: User.votes must be eagerly loaded (add selectinload(User.votes))")
    return UserPrivate(
        id=user.id,
        display_name=user.display_name,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        phone=user.phone,
        vote_ids=[v.id for v in user.votes],
        has_ysws_pii=has_ysws_pii(user),
        is_superadmin=user.is_superadmin,
    )


# ─── Write schemas (API requests) ────────────────────────────────────────────

class _UserWriteBase(SQLModel):
    """Common optional fields shared by UserSignup and UserUpdate.
    first_name is handled separately — required at signup, optional on update."""
    display_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    street_1: str | None = None
    street_2: str | None = None
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None
    country: str | None = None
    dob: date | None = None


class UserSignup(_UserWriteBase):
    """Request body for user signup."""
    email: str
    first_name: str


class UserUpdate(_UserWriteBase):
    """Request body for profile update. None fields are excluded from the update."""
    first_name: str | None = None
