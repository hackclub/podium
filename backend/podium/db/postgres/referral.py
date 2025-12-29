"""
Referral model.

A Referral captures how a user heard about an event when they join.
"""

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel, Relationship

if TYPE_CHECKING:
    from podium.db.postgres.user import User
    from podium.db.postgres.event import Event


class Referral(SQLModel, table=True):
    """Referral info - maps to 'referrals' table."""

    __tablename__: str = "referrals"

    # Primary key - auto-generated UUID
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # For migration from Airtable (temporary)
    airtable_id: str | None = Field(default=None, max_length=32, unique=True, index=True)

    # How the user heard about the event
    content: str = Field(default="")

    # Foreign keys
    user_id: UUID = Field(foreign_key="users.id")
    event_id: UUID = Field(foreign_key="events.id")

    # Relationships
    user: "User" = Relationship(back_populates="referrals")
    event: "Event" = Relationship(back_populates="referrals")
