"""
Podium models using ormar ORM.

ormar provides: single model for DB schema + Pydantic validation, full async, Alembic support.

Usage:
    from podium.db.models_ormar import User, Event, Project, Vote, Referral
"""

from datetime import date
from typing import List, Optional
from uuid import uuid4, UUID

import databases
import sqlalchemy
import ormar
    
from podium.config import settings

# Database connection
DATABASE_URL = settings.database_url  # postgres://user:pass@host:5432/podium

database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()


# =============================================================================
# USER
# =============================================================================


class User(ormar.Model):
    ormar_config = ormar.OrmarConfig(
        tablename="users",
        database=database,
        metadata=metadata,
    )

    id: UUID = ormar.UUID(primary_key=True, default=uuid4)
    airtable_id: Optional[str] = ormar.String(
        max_length=32, nullable=True, unique=True, index=True
    )
    email: str = ormar.String(max_length=255, unique=True, index=True)
    display_name: str = ormar.String(max_length=255, default="")
    first_name: str = ormar.String(max_length=50)
    last_name: str = ormar.String(max_length=50, default="")
    phone: str = ormar.String(max_length=20, default="")
    street_1: str = ormar.String(max_length=255, default="")
    street_2: str = ormar.String(max_length=255, default="")
    city: str = ormar.String(max_length=100, default="")
    state: str = ormar.String(max_length=100, default="")
    zip_code: str = ormar.String(max_length=20, default="")
    country: str = ormar.String(max_length=100, default="")
    dob: Optional[date] = ormar.Date(nullable=True)


# =============================================================================
# EVENT
# =============================================================================


class Event(ormar.Model):
    ormar_config = ormar.OrmarConfig(
        tablename="events",
        database=database,
        metadata=metadata,
    )

    id: UUID = ormar.UUID(primary_key=True, default=uuid4)
    airtable_id: Optional[str] = ormar.String(
        max_length=32, nullable=True, unique=True, index=True
    )
    name: str = ormar.String(max_length=255)
    slug: str = ormar.String(max_length=50, unique=True, index=True)
    description: str = ormar.Text(default="")
    join_code: str = ormar.String(max_length=20, unique=True)
    votable: bool = ormar.Boolean(default=False)
    leaderboard_enabled: bool = ormar.Boolean(default=False)
    demo_links_optional: bool = ormar.Boolean(default=False)
    ysws_checks_enabled: bool = ormar.Boolean(default=False)
    feature_flags_csv: str = ormar.String(max_length=500, default="")

    # Relationships
    owner: User = ormar.ForeignKey(User, related_name="owned_events")

    # Many-to-many: attendees (ormar auto-creates junction table)
    attendees: List[User] = ormar.ManyToMany(
        User,
        related_name="events_attending",
    )

    @property
    def feature_flags_list(self) -> List[str]:
        if not self.feature_flags_csv:
            return []
        return [f.strip() for f in self.feature_flags_csv.split(",") if f.strip()]


# =============================================================================
# PROJECT
# =============================================================================


class Project(ormar.Model):
    ormar_config = ormar.OrmarConfig(
        tablename="projects",
        database=database,
        metadata=metadata,
    )

    id: UUID = ormar.UUID(primary_key=True, default=uuid4)
    airtable_id: Optional[str] = ormar.String(
        max_length=32, nullable=True, unique=True, index=True
    )
    name: str = ormar.String(max_length=255)
    repo: str = ormar.String(max_length=500)
    image_url: str = ormar.String(max_length=500)
    demo: str = ormar.String(max_length=500, default="")
    description: str = ormar.Text(default="")
    join_code: str = ormar.String(max_length=20, unique=True)
    hours_spent: int = ormar.Integer(default=0)
    points: int = ormar.Integer(default=0, index=True)
    cached_auto_quality: Optional[dict] = ormar.JSON(nullable=True)

    # Relationships
    owner: User = ormar.ForeignKey(User, related_name="owned_projects")
    event: Event = ormar.ForeignKey(Event, related_name="projects")

    # Many-to-many: collaborators (ormar auto-creates junction table)
    collaborators: List[User] = ormar.ManyToMany(
        User,
        related_name="projects_collaborating",
    )


# =============================================================================
# VOTE (not M2M - it's a standalone entity with FKs)
# =============================================================================


class Vote(ormar.Model):
    ormar_config = ormar.OrmarConfig(
        tablename="votes",
        database=database,
        metadata=metadata,
        constraints=[ormar.UniqueColumns("voter", "project")],
    )

    id: UUID = ormar.UUID(primary_key=True, default=uuid4)
    airtable_id: Optional[str] = ormar.String(
        max_length=32, nullable=True, unique=True, index=True
    )
    voter: User = ormar.ForeignKey(User, related_name="votes")
    project: Project = ormar.ForeignKey(Project, related_name="votes")
    event: Event = ormar.ForeignKey(Event, related_name="votes")  # denormalized


# =============================================================================
# REFERRAL (not M2M - it's a standalone entity with FKs)
# =============================================================================


class Referral(ormar.Model):
    ormar_config = ormar.OrmarConfig(
        tablename="referrals",
        database=database,
        metadata=metadata,
    )

    id: UUID = ormar.UUID(primary_key=True, default=uuid4)
    airtable_id: Optional[str] = ormar.String(
        max_length=32, nullable=True, unique=True, index=True
    )
    content: str = ormar.Text(default="")
    user: User = ormar.ForeignKey(User, related_name="referrals")
    event: Event = ormar.ForeignKey(Event, related_name="referrals")


# =============================================================================
# PYDANTIC SCHEMAS (for API request/response)
# =============================================================================
# ormar models ARE Pydantic models, but for partial updates or custom 
# responses you may want separate schemas:

from pydantic import BaseModel  # noqa: E402


class UserPublic(BaseModel):
    id: UUID
    display_name: str

    class Config:
        from_attributes = True


class UserPrivate(UserPublic):
    email: str
    first_name: str
    last_name: str
    phone: str = ""

    class Config:
        from_attributes = True


class EventPublic(BaseModel):
    id: UUID
    name: str
    slug: str
    description: str
    votable: bool
    leaderboard_enabled: bool
    demo_links_optional: bool

    class Config:
        from_attributes = True


class EventPrivate(EventPublic):
    join_code: str
    owner_id: UUID

    class Config:
        from_attributes = True


class ProjectPublic(BaseModel):
    id: UUID
    name: str
    repo: str
    image_url: str
    demo: str
    description: str
    points: int

    class Config:
        from_attributes = True


# =============================================================================
# DATABASE LIFECYCLE
# =============================================================================


async def init_db():
    """Initialize database connection."""
    await database.connect()


async def close_db():
    """Close database connection."""
    await database.disconnect()
