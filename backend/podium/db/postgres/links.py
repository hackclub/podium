"""
Junction tables for many-to-many relationships.

SQLModel requires explicit link tables for M2M - there's no auto-creation.
These connect: Event <-> User (attendees) and Project <-> User (collaborators).
"""

from uuid import UUID

from sqlmodel import Field, SQLModel


class EventAttendeeLink(SQLModel, table=True):
    """Links events to their attendees (many-to-many)."""

    __tablename__: str = "event_attendees"

    event_id: UUID = Field(foreign_key="events.id", primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", primary_key=True)


class ProjectCollaboratorLink(SQLModel, table=True):
    """Links projects to their collaborators (many-to-many)."""

    __tablename__: str = "project_collaborators"

    project_id: UUID = Field(foreign_key="projects.id", primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", primary_key=True)
