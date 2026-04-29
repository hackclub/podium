"""
Project model and API schemas.

A Project is a hackathon submission that belongs to an Event.
"""

from typing import TYPE_CHECKING
from urllib.parse import urlparse
from uuid import UUID, uuid4

from pydantic import computed_field
from sqlmodel import Field, SQLModel, Relationship

from podium.constants import ValidationStatus
from podium.db.postgres.links import ProjectCollaboratorLink


def github_username_from_repo(repo_url: str) -> str:
    """Extract the GitHub username from a github.com repo URL.

    Returns empty string for non-GitHub URLs or malformed input.
    Example: https://github.com/hackclub/sprig -> 'hackclub'
    """
    if not repo_url:
        return ""
    try:
        p = urlparse(repo_url)
        if p.netloc in ("github.com", "www.github.com"):
            parts = p.path.strip("/").split("/")
            if parts and parts[0]:
                return parts[0]
    except Exception:
        pass
    return ""

if TYPE_CHECKING:
    from podium.db.postgres.user import User
    from podium.db.postgres.event import Event
    from podium.db.postgres.vote import Vote



class Project(SQLModel, table=True):
    """Hackathon project submission - maps to 'projects' table."""

    __tablename__: str = "projects"

    # Primary key - auto-generated UUID
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Core fields
    name: str = Field(max_length=255)
    repo: str = Field(default="")  # TEXT - URLs can be long
    image_url: str = Field()  # TEXT - URLs with tokens can be very long
    demo: str = Field(default="")  # TEXT - URLs can be long
    description: str = Field(default="")
    join_code: str = Field(max_length=20, unique=True)
    hours_spent: int = Field(default=0)

    # Background validation result — updated asynchronously after project save
    validation_status: str = Field(default=ValidationStatus.PENDING, max_length=20)
    validation_message: str = Field(default="")

    # Computed field pattern: use @computed_field for derived values.
    # Requires eager-loading the relationship: select(Project).options(selectinload(Project.votes))
    @computed_field  # type: ignore[prop-decorator]
    @property
    def points(self) -> int:
        """Vote count - computed from votes relationship."""
        return len(self.votes)

    @computed_field
    @property
    def owner_display_name(self) -> str:
        """Owner's display name — requires selectinload(Project.owner)."""
        if not self.owner:
            return ""
        return self.owner.display_name

    @computed_field
    @property
    def collaborator_display_names(self) -> list[str]:
        """Collaborator display names — requires selectinload(Project.collaborators)."""
        return [c.display_name for c in (self.collaborators or [])]

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
    owner_id: UUID
    owner_display_name: str = ""
    collaborator_display_names: list[str] = []


class ProjectPrivate(ProjectPublic):
    """Private project info - visible to owner and collaborators."""

    join_code: str
    hours_spent: int
    event_id: UUID
    validation_status: str
    validation_message: str


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
