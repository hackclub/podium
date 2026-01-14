"""
PostgreSQL models and database utilities.

This module exports all SQLModel table models and database utilities.
Import from here to get everything you need:

    from podium.db.postgres import User, Event, Project, get_session

Query patterns:
    # PK lookup (preferred for single ID)
    user = await session.get(User, user_id)

    # Field lookup (use typed helpers)
    user = await scalar_one_or_none(session, select(User).where(User.email == email))
    projects = await scalar_all(session, select(Project).where(Project.event_id == eid))
"""

from podium.db.postgres.base import get_session, engine, init_db, scalar_one_or_none, scalar_all
from podium.db.postgres.links import EventAttendeeLink, ProjectCollaboratorLink
from podium.db.postgres.user import User, UserPublic, UserPrivate, UserSignup, UserUpdate
from podium.db.postgres.event import Event, EventPublic, EventPrivate, EventCreate, EventUpdate
from podium.db.postgres.project import (
    Project,
    ProjectPublic,
    ProjectPrivate,
    ProjectCreate,
    ProjectUpdate,
)
from podium.db.postgres.vote import Vote
from podium.db.postgres.referral import Referral

__all__ = [
    # Database utilities
    "get_session",
    "engine",
    "init_db",
    "scalar_one_or_none",
    "scalar_all",
    # Link tables (many-to-many)
    "EventAttendeeLink",
    "ProjectCollaboratorLink",
    # User
    "User",
    "UserPublic",
    "UserPrivate",
    "UserSignup",
    "UserUpdate",
    # Event
    "Event",
    "EventPublic",
    "EventPrivate",
    "EventCreate",
    "EventUpdate",
    # Project
    "Project",
    "ProjectPublic",
    "ProjectPrivate",
    "ProjectCreate",
    "ProjectUpdate",
    # Vote & Referral
    "Vote",
    "Referral",
]
