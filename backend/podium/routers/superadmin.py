"""
Superadmin endpoints. Requires is_superadmin=True on the authenticated user.

Superadmins can:
  - List all events (including soft-deleted)
  - Create real events (not limited to test endpoints)
  - Soft-delete events (sets deleted_at, hides from public listings)
  - Update any event field including owner (by email)
  - List all users

Regular admin endpoints (admin.py) already grant superadmins full owner access
to any event via the get_owned_event helper.
"""

from datetime import datetime, UTC
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import ConfigDict
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from pydantic import BaseModel
from secrets import token_urlsafe
from slugify import slugify
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload

from podium.db.postgres import (
    User,
    Event,
    EventPrivate,
    EventUpdate,
    get_session,
    scalar_one_or_none,
)
from podium.routers.auth import get_current_user
from podium.constants import BAD_ACCESS, EventPhase

router = APIRouter(prefix="/superadmin", tags=["superadmin"])


async def require_superadmin(user: Annotated[User, Depends(get_current_user)]) -> User:
    """Dependency: raise 403 if the user is not a superadmin."""
    if not user.is_superadmin:
        raise BAD_ACCESS
    return user


class EventCreate(BaseModel):
    name: str
    description: str = ""
    phase: str = EventPhase.DRAFT
    demo_links_optional: bool = False
    repo_validation: str = "github"
    demo_validation: str = "none"
    custom_validator: str | None = None
    feature_flags_csv: str = ""


class SuperadminEventUpdate(EventUpdate):
    """EventUpdate extended with superadmin-only fields."""
    owner_email: str | None = None


class UserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: str
    display_name: str
    is_superadmin: bool


@router.get("/events")
async def list_all_events(
    user: Annotated[User, Depends(require_superadmin)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Page[EventPrivate]:
    """List all events, including soft-deleted ones."""
    return await paginate(session, select(Event).options(selectinload(Event.projects)))


@router.post("/events")
async def create_event(
    event_data: EventCreate,
    user: Annotated[User, Depends(require_superadmin)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> EventPrivate:
    """Create a real event as the requesting superadmin user."""
    base_slug = slugify(event_data.name)[:40] or "event"
    slug = f"{base_slug}-{token_urlsafe(4)}"

    event = Event(
        **event_data.model_dump(),
        slug=slug,
        owner_id=user.id,
    )
    session.add(event)
    await session.commit()
    await session.refresh(event)

    stmt = select(Event).where(Event.id == event.id).options(selectinload(Event.projects))
    event = await scalar_one_or_none(session, stmt)
    return EventPrivate.model_validate(event)


@router.delete("/events/{event_id}")
async def soft_delete_event(
    event_id: Annotated[UUID, Path(title="Event ID")],
    user: Annotated[User, Depends(require_superadmin)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Soft-delete an event (sets deleted_at). The event is hidden from public listings."""
    event = await session.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.deleted_at is not None:
        raise HTTPException(status_code=400, detail="Event is already deleted")

    event.deleted_at = datetime.now(UTC)
    await session.commit()
    return {"message": "Event soft-deleted", "deleted_at": event.deleted_at.isoformat()}


@router.patch("/events/{event_id}")
async def update_event(
    event_id: Annotated[UUID, Path(title="Event ID")],
    update: SuperadminEventUpdate,
    user: Annotated[User, Depends(require_superadmin)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> EventPrivate:
    """Update any event field. Use owner_email to transfer ownership."""
    event = await session.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    data = update.model_dump(exclude_unset=True)

    if "owner_email" in data:
        owner_email = data.pop("owner_email")
        new_owner = await scalar_one_or_none(session, select(User).where(User.email == owner_email))
        if not new_owner:
            raise HTTPException(status_code=404, detail=f"User '{owner_email}' not found")
        event.owner_id = new_owner.id

    for field, value in data.items():
        setattr(event, field, value)

    await session.commit()

    stmt = select(Event).where(Event.id == event.id).options(selectinload(Event.projects))
    event = await scalar_one_or_none(session, stmt)
    return EventPrivate.model_validate(event)


@router.get("/users")
async def list_users(
    user: Annotated[User, Depends(require_superadmin)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Page[UserSummary]:
    """List all users."""
    return await paginate(session, select(User))
