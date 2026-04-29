"""
Superadmin endpoints. Requires is_superadmin=True on the authenticated user.

Superadmins can:
  - List all events (including soft-deleted)
  - Create real events (not limited to test endpoints)
  - Soft-delete events (sets deleted_at, hides from public listings)
  - Update any event field including owner (by email) and feature flags
  - Export project + owner PII as CSV for YSWS unified DB import
  - List all users

Regular admin endpoints (admin.py) already grant superadmins full owner access
to any event via the get_owned_event helper.
"""

import csv
import io
from datetime import datetime, UTC
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.responses import StreamingResponse
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
    scalar_all,
)
from podium.db.postgres.project import Project, github_username_from_repo
from podium.db.postgres.queries import list_active_events
from podium.routers.auth import get_current_user
from podium.constants import BAD_ACCESS, EventPhase


_CSV_COLUMNS = [
    "First Name", "Last Name", "Email",
    "Playable URL", "Code URL", "Screenshot", "Description",
    "GitHub Username",
    "Address (Line 1)", "Address (Line 2)", "City", "State / Province",
    "Country", "ZIP / Postal Code", "Birthday",
    "Override Hours Spent",
]

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


@router.get("/export-csv")
async def export_projects_csv(
    user: Annotated[User, Depends(require_superadmin)],
    session: Annotated[AsyncSession, Depends(get_session)],
    event_id: UUID | None = Query(default=None),
    series: str | None = Query(default=None),
) -> StreamingResponse:
    """Export project + owner PII as CSV for YSWS unified DB import.

    Pass either event_id (single event) or series (all active events with that feature flag).
    All rows are included regardless of missing fields — validate downstream.
    """
    if not event_id and not series:
        raise HTTPException(status_code=400, detail="Provide either event_id or series")
    if event_id and series:
        raise HTTPException(status_code=400, detail="Provide either event_id or series, not both")

    date_str = datetime.now(UTC).strftime("%Y-%m-%d")

    if event_id:
        event = await session.get(Event, event_id)
        slug = event.slug if event else str(event_id)
        stmt = (
            select(Project)
            .where(Project.event_id == event_id)
            .options(selectinload(Project.owner))
        )
        filename = f"projects-{slug}-{date_str}.csv"
    else:
        all_events = await list_active_events(session)
        matching_ids = [e.id for e in all_events if series in e.feature_flags_list]
        if not matching_ids:
            raise HTTPException(status_code=404, detail=f"No active events found with series '{series}'")
        stmt = (
            select(Project)
            .where(Project.event_id.in_(matching_ids))
            .options(selectinload(Project.owner))
        )
        filename = f"projects-{series}-{date_str}.csv"

    projects = await scalar_all(session, stmt)

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=_CSV_COLUMNS)
    writer.writeheader()

    for project in projects:
        owner = project.owner
        writer.writerow({
            "First Name": owner.first_name,
            "Last Name": owner.last_name,
            "Email": owner.email,
            "Playable URL": project.demo,
            "Code URL": project.repo,
            "Screenshot": project.image_url,
            "Description": project.description,
            "GitHub Username": github_username_from_repo(project.repo),
            "Address (Line 1)": owner.street_1,
            "Address (Line 2)": owner.street_2,
            "City": owner.city,
            "State / Province": owner.state,
            "Country": owner.country,
            "ZIP / Postal Code": owner.zip_code,
            "Birthday": owner.dob.isoformat() if owner.dob else "",
            "Override Hours Spent": project.hours_spent or "",
        })

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/users")
async def list_users(
    user: Annotated[User, Depends(require_superadmin)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Page[UserSummary]:
    """List all users."""
    return await paginate(session, select(User))
