"""
Project model and API schemas.

A Project is a hackathon submission that belongs to an Event.
"""

from typing import Any, TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel, Relationship

from podium.db.postgres.links import ProjectCollaboratorLink

if TYPE_CHECKING:
    from podium.db.postgres.user import User
    from podium.db.postgres.event import Event
    from podium.db.postgres.vote import Vote


class Project(SQLModel, table=True):
    """Hackathon project submission - maps to 'projects' table."""

    __tablename__: str = "projects"

    # Primary key - auto-generated UUID
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # For migration from Airtable (temporary)
    airtable_id: str | None = Field(default=None, max_length=32, unique=True, index=True)

    # Core fields
    name: str = Field(max_length=255)
    repo: str = Field(default="")  # TEXT - URLs can be long
    image_url: str = Field(default="")  # TEXT - URLs with tokens can be very long
    demo: str = Field(default="")  # TEXT - URLs can be long
    description: str = Field(default="")
    join_code: str = Field(max_length=20, unique=True)
    hours_spent: int = Field(default=0)
    points: int = Field(default=0, index=True)

    # Cached results from automated quality checks (JSONB for flexibility)
    cached_auto_quality: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSONB)
    )

    # Foreign keys
    owner_id: UUID = Field(foreign_key="users.id")
    event_id: UUID = Field(foreign_key="events.id")

    # Relationships
    owner: "User" = Relationship(back_populates="owned_projects")
    event: "Event" = Relationship(back_populates="projects")
    collaborators: list["User"] = Relationship(
        back_populates="projects_collaborating", link_model=ProjectCollaboratorLink
    )
    votes: list["Vote"] = Relationship(back_populates="project")


# =============================================================================
# API SCHEMAS
# =============================================================================


class ProjectPublic(SQLModel):
    """Public project info - visible to anyone."""

    id: UUID
    name: str
    repo: str
    image_url: str
    demo: str
    description: str
    points: int


class ProjectPrivate(ProjectPublic):
    """Private project info - visible to owner and collaborators."""

    join_code: str
    hours_spent: int
    owner_id: UUID
    event_id: UUID
    cached_auto_quality: dict[str, Any] | None = None


class ProjectCreate(SQLModel):
    """Request body for creating a project."""

    name: str
    repo: str
    image_url: str
    demo: str = ""
    description: str = ""
    hours_spent: int = 0
    event_id: UUID


class ProjectUpdate(SQLModel):
    """Request body for updating a project. All fields optional."""

    name: str | None = None
    repo: str | None = None
    image_url: str | None = None
    demo: str | None = None
    description: str | None = None
    hours_spent: int | None = None
