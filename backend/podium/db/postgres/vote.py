"""
Vote model.

A Vote records when a user votes for a project in an event.
Each user can only vote once per project (enforced by unique constraint).
"""

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel, Relationship, UniqueConstraint

if TYPE_CHECKING:
    from podium.db.postgres.user import User
    from podium.db.postgres.event import Event
    from podium.db.postgres.project import Project


class Vote(SQLModel, table=True):
    """Vote for a project - maps to 'votes' table."""

    __tablename__: str = "votes"
    __table_args__ = (UniqueConstraint("voter_id", "project_id"),)

    # Primary key - auto-generated UUID
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # For migration from Airtable (temporary)
    airtable_id: str | None = Field(default=None, max_length=32, unique=True, index=True)

    # Foreign keys
    voter_id: UUID = Field(foreign_key="users.id")
    project_id: UUID = Field(foreign_key="projects.id")
    event_id: UUID = Field(foreign_key="events.id")  # denormalized for faster queries

    # Relationships
    voter: "User" = Relationship(back_populates="votes")
    project: "Project" = Relationship(back_populates="votes")
    event: "Event" = Relationship(back_populates="votes")
