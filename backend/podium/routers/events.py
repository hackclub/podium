import random
from secrets import token_urlsafe
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel
from slugify import slugify
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload

from podium.routers.auth import get_current_user
from podium.db.postgres import (
    User,
    Event,
    EventPublic,
    EventPrivate,
    EventCreate,
    EventUpdate,
    Project,
    ProjectPublic,
    Vote,
    Referral,
    get_session,
    scalar_one_or_none,
    scalar_all,
)
from podium.constants import BAD_AUTH, BAD_ACCESS, Slug

router = APIRouter(prefix="/events", tags=["events"])


class UserEvents(BaseModel):
    owned_events: list[EventPrivate]
    attending_events: list[EventPublic]


class CreateVotes(BaseModel):
    projects: list[UUID]
    event: UUID


@router.get("/{event_id}")
async def get_event_endpoint(
    event_id: Annotated[UUID, Path(title="Event ID")],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> EventPublic:
    """Get a public event by its ID."""
    event = await session.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return EventPublic.model_validate(event)


@router.get("/")
async def get_attending_events(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserEvents:
    """Get events the current user owns and attends."""
    stmt = (
        select(User)
        .where(User.id == user.id)
        .options(selectinload(User.owned_events), selectinload(User.events_attending))
    )
    u = await scalar_one_or_none(session, stmt)
    if not u:
        raise BAD_AUTH
    return UserEvents(
        owned_events=[EventPrivate.model_validate(e) for e in u.owned_events],
        attending_events=[EventPublic.model_validate(e) for e in u.events_attending],
    )


@router.post("/")
async def create_event(
    event: EventCreate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Create a new event."""
    slug = slugify(event.name, lowercase=True, separator="-")
    existing = await scalar_one_or_none(session, select(Event).where(Event.slug == slug))
    if existing:
        raise HTTPException(status_code=400, detail="Event slug already exists")

    while True:
        join_code = token_urlsafe(3).upper()
        code_exists = await scalar_one_or_none(
            session, select(Event).where(Event.join_code == join_code)
        )
        if not code_exists:
            break

    new_event = Event.model_validate(
        event,
        update={
            "slug": slug,
            "join_code": join_code,
            "owner_id": user.id,
        },
    )
    session.add(new_event)
    await session.commit()
    await session.refresh(new_event)
    return {"id": str(new_event.id), "slug": new_event.slug, "join_code": new_event.join_code}


@router.post("/attend")
async def attend_event(
    join_code: Annotated[str, Query(description="Event join code")],
    referral: Annotated[str, Query(description="How did you hear about this event?")],
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Attend an event using a join code."""
    stmt = (
        select(Event)
        .where(Event.join_code == join_code.upper())
        .options(selectinload(Event.attendees))
    )
    event = await scalar_one_or_none(session, stmt)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if user in event.attendees:
        raise HTTPException(status_code=400, detail="User already attending event")

    event.attendees.append(user)

    if referral:
        session.add(Referral(content=referral, user_id=user.id, event_id=event.id))

    await session.commit()
    return {"message": "Successfully joined event", "event_id": str(event.id)}


@router.put("/{event_id}")
async def update_event(
    event_id: Annotated[UUID, Path(title="Event ID")],
    event_update: EventUpdate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Update an event."""
    event = await session.get(Event, event_id)
    if not event or event.owner_id != user.id:
        raise BAD_ACCESS

    update_data = event_update.model_dump(exclude_unset=True, exclude_none=True)
    event.sqlmodel_update(update_data)

    await session.commit()
    return {"message": "Event updated"}


@router.delete("/{event_id}")
async def delete_event(
    event_id: Annotated[UUID, Path(title="Event ID")],
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Delete an event."""
    event = await session.get(Event, event_id)
    if not event or event.owner_id != user.id:
        raise BAD_ACCESS

    await session.delete(event)
    await session.commit()
    return {"message": "Event deleted"}


@router.post("/vote")
async def vote(
    votes: CreateVotes,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Vote for projects in an event."""
    stmt = (
        select(Event)
        .where(Event.id == votes.event)
        .options(selectinload(Event.attendees), selectinload(Event.projects))
    )
    event = await scalar_one_or_none(session, stmt)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if user not in event.attendees:
        raise BAD_ACCESS

    # Dedupe project IDs to prevent voting for same project twice in one request
    unique_project_ids = list(dict.fromkeys(votes.projects))

    existing_votes = await scalar_all(
        session,
        select(Vote).where(Vote.event_id == event.id, Vote.voter_id == user.id),
    )

    # Check total votes (existing + new) doesn't exceed limit
    if len(existing_votes) + len(unique_project_ids) > event.max_votes_per_user:
        remaining = event.max_votes_per_user - len(existing_votes)
        raise HTTPException(
            status_code=400,
            detail=f"Cannot vote for {len(unique_project_ids)} projects. You have {remaining} vote(s) remaining.",
        )

    for project_id in unique_project_ids:
        stmt = (
            select(Project)
            .where(Project.id == project_id)
            .options(selectinload(Project.collaborators))
        )
        project = await scalar_one_or_none(session, stmt)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        if project.event_id != event.id:
            raise HTTPException(status_code=400, detail="Project is not in the event")

        already_voted = await scalar_one_or_none(
            session,
            select(Vote).where(
                Vote.voter_id == user.id, Vote.event_id == event.id, Vote.project_id == project_id
            ),
        )
        if already_voted:
            raise HTTPException(status_code=400, detail="User has already voted for this project")

        if user.id == project.owner_id or user in project.collaborators:
            raise HTTPException(status_code=403, detail="User cannot vote for their own project")

        session.add(Vote(voter_id=user.id, project_id=project_id, event_id=event.id))
        project.points += 1

    await session.commit()
    return {"message": "Votes recorded"}


@router.get("/{event_id}/projects", response_model=list[ProjectPublic])
async def get_event_projects(
    event_id: Annotated[UUID, Path(title="Event ID")],
    leaderboard: Annotated[bool, Query(description="Sort by points if true")],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[ProjectPublic]:
    """Get projects for an event."""
    event = await session.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    projects = await scalar_all(
        session, select(Project).where(Project.event_id == event_id)
    )

    if leaderboard:
        if not event.leaderboard_enabled:
            raise HTTPException(status_code=403, detail="Leaderboard is not enabled")
        projects.sort(key=lambda p: p.points, reverse=True)
    else:
        random.shuffle(projects)

    return [ProjectPublic.model_validate(p) for p in projects]


@router.get("/id/{slug}", response_model=str)
async def get_at_id(
    slug: Annotated[Slug, Path(title="Event Slug")],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> str:
    """Get an event's ID by its slug."""
    event = await scalar_one_or_none(session, select(Event).where(Event.slug == slug))
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return str(event.id)
