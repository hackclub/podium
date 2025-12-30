"""
Junction tables for many-to-many relationships.

SQLModel requires explicit link tables for M2M - there's no auto-creation.
These connect: Event <-> User (attendees) and Project <-> User (collaborators).

## Why surrogate PKs?

These tables use a surrogate `id` PK instead of a composite PK on (event_id, user_id).
This is required for Mathesar's "Extend" feature, which only works with junction tables
that have exactly 3 columns: 1 single-column PK + 2 FKs.

The logical uniqueness constraint on (event_id, user_id) is preserved via UniqueConstraint.
See migration e10bb6a39187 for the schema change details.
"""

from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel, UniqueConstraint


class EventAttendeeLink(SQLModel, table=True):
    """Links events to their attendees (many-to-many)."""

    __tablename__: str = "event_attendees"
    __table_args__ = (UniqueConstraint("event_id", "user_id"),)

    # Surrogate PK for Mathesar Extend compatibility (requires single-column PK)
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    event_id: UUID = Field(foreign_key="events.id")
    user_id: UUID = Field(foreign_key="users.id")


class ProjectCollaboratorLink(SQLModel, table=True):
    """Links projects to their collaborators (many-to-many)."""

    __tablename__: str = "project_collaborators"
    __table_args__ = (UniqueConstraint("project_id", "user_id"),)

    # Surrogate PK for Mathesar Extend compatibility (requires single-column PK)
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="projects.id")
    user_id: UUID = Field(foreign_key="users.id")
