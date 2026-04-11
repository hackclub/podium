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

from podium.config import settings
from podium.routers.auth import get_current_user
from podium.db.postgres import (
    User,
    Event,
    EventPublic,
    Project,
    ProjectPublic,
    Vote,
    get_session,
    get_ro_session,
    scalar_one_or_none,
    scalar_all,
)
from podium.constants import BAD_AUTH, BAD_ACCESS, Slug, EventPhase
from podium.cache import cache_get, cache_set, cache_delete

router = APIRouter(prefix="/events", tags=["events"])


class UserEvents(BaseModel):
    attending_events: list[EventPublic]


class CreateVotes(BaseModel):
    projects: list[UUID]
    event: UUID


@router.get("/official")
async def list_official_events(
    session: Annotated[AsyncSession, Depends(get_ro_session)],
) -> list[EventPublic]:
    """List all official events for the current series (flagship + satellites)."""
    active_series = settings.active_event_series
    if not active_series:
        return []

    all_events = await scalar_all(
        session,
        select(Event).options(selectinload(Event.projects)),
    )

    official_events = [
        EventPublic.model_validate(e)
        for e in all_events
        if active_series in e.feature_flags_list
    ]

    return official_events


@router.get("/{event_id}")
async def get_event_endpoint(
    event_id: Annotated[UUID, Path(title="Event ID")],
    session: Annotated[AsyncSession, Depends(get_ro_session)],
) -> EventPublic:
    """Get a public event by its ID."""
    stmt = select(Event).where(Event.id == event_id).options(selectinload(Event.projects))
    event = await scalar_one_or_none(session, stmt)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return EventPublic.model_validate(event)


@router.get("/")
async def get_attending_events(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserEvents:
    """Get events the current user attends."""
    stmt = (
        select(User)
        .where(User.id == user.id)
        .options(
            selectinload(User.events_attending).selectinload(Event.projects),
        )
    )
    u = await scalar_one_or_none(session, stmt)
    if not u:
        raise BAD_AUTH
    return UserEvents(
        attending_events=[EventPublic.model_validate(e) for e in u.events_attending],
    )


@router.post("/{event_id}/attend")
async def attend_event(
    event_id: Annotated[UUID, Path(title="Event ID")],
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Attend an official event by ID."""
    active_series = settings.active_event_series
    if not active_series:
        raise HTTPException(status_code=400, detail="No active event series configured")

    stmt = (
        select(Event)
        .where(Event.id == event_id)
        .options(selectinload(Event.attendees), selectinload(Event.projects))
    )
    event = await scalar_one_or_none(session, stmt)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if active_series not in event.feature_flags_list:
        raise HTTPException(status_code=400, detail=f"Event is not part of the active series (expected {active_series!r} in {event.feature_flags_list!r})")

    if user in event.attendees:
        return {"message": "Already attending this event", "event_id": str(event.id)}

    event.attendees.append(user)
    await session.commit()

    return {"message": "Successfully joined event", "event_id": str(event.id)}


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

    if event.phase != EventPhase.VOTING:
        raise HTTPException(status_code=403, detail="Voting is not open for this event")

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

    await session.commit()
    # Invalidate cached leaderboard so next request reflects the new votes
    await cache_delete(f"leaderboard:{event.id}")
    return {"message": "Votes recorded"}


@router.get("/{event_id}/projects", response_model=list[ProjectPublic])
async def get_event_projects(
    event_id: Annotated[UUID, Path(title="Event ID")],
    leaderboard: Annotated[bool, Query(description="Sort by points if true")],
    session: Annotated[AsyncSession, Depends(get_ro_session)],
) -> list[ProjectPublic]:
    """Get projects for an event. Leaderboard results are cached for 30s."""
    event = await session.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if leaderboard:
        if event.phase != EventPhase.CLOSED:
            raise HTTPException(status_code=403, detail="Leaderboard is only available after voting closes")

        # Serve from cache if available (30s TTL is fine for leaderboards)
        cache_key = f"leaderboard:{event_id}"
        cached = await cache_get(cache_key)
        if cached is not None:
            return cached

    projects = await scalar_all(
        session,
        select(Project)
        .where(Project.event_id == event_id)
        .options(selectinload(Project.votes)),
    )

    if leaderboard:
        projects.sort(key=lambda p: p.points, reverse=True)
        result = [ProjectPublic.model_validate(p).model_dump() for p in projects]
        await cache_set(cache_key, result, ttl=30)
        return result  # type: ignore[return-value]
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


# =============================================================================
# TEST-ONLY ENDPOINTS
# =============================================================================


class TestEventCreate(BaseModel):
    """Request body for creating a test event."""

    name: str
    description: str = ""


@router.post("/test/create")
async def create_test_event(
    event_data: TestEventCreate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> EventPublic:
    """Create a test event. Only available when enable_test_endpoints is true."""
    if not getattr(settings, "enable_test_endpoints", False):
        raise HTTPException(status_code=404, detail="Not found")

    active_series = settings.active_event_series
    if not active_series:
        raise HTTPException(status_code=400, detail="No active event series configured")

    base_slug = slugify(event_data.name)[:40]
    slug = f"{base_slug}-{token_urlsafe(4)}"

    event = Event(
        name=event_data.name,
        slug=slug,
        description=event_data.description,
        owner_id=user.id,
        phase=EventPhase.VOTING,  # test events start in voting phase for e2e tests
        demo_links_optional=True,
        feature_flags_csv=active_series,
    )

    session.add(event)
    await session.commit()
    await session.refresh(event)

    # Reload with projects relationship for max_votes_per_user computation
    stmt = select(Event).where(Event.id == event.id).options(selectinload(Event.projects))
    event = await scalar_one_or_none(session, stmt)

    return EventPublic.model_validate(event)


@router.post("/test/cleanup")
async def cleanup_test_data(
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Delete all test data created by e2e tests. Only available when enable_test_endpoints is true."""
    if not getattr(settings, "enable_test_endpoints", False):
        raise HTTPException(status_code=404, detail="Not found")

    from sqlalchemy import text

    # Delete test users (pattern: test+pw*@example.com, organizer+*@test.local, attendee+*@test.local)
    await session.execute(
        text("""
            DELETE FROM votes WHERE voter_id IN (
                SELECT id FROM users WHERE email LIKE 'test+pw%@example.com'
                OR email LIKE 'organizer+%@test.local'
                OR email LIKE 'attendee+%@test.local'
            )
        """)
    )
    await session.execute(
        text("""
            DELETE FROM votes WHERE project_id IN (
                SELECT id FROM projects WHERE owner_id IN (
                    SELECT id FROM users WHERE email LIKE 'test+pw%@example.com'
                    OR email LIKE 'organizer+%@test.local'
                    OR email LIKE 'attendee+%@test.local'
                )
            )
        """)
    )
    await session.execute(
        text("""
            DELETE FROM project_collaborators WHERE user_id IN (
                SELECT id FROM users WHERE email LIKE 'test+pw%@example.com'
                OR email LIKE 'organizer+%@test.local'
                OR email LIKE 'attendee+%@test.local'
            )
        """)
    )
    await session.execute(
        text("""
            DELETE FROM projects WHERE owner_id IN (
                SELECT id FROM users WHERE email LIKE 'test+pw%@example.com'
                OR email LIKE 'organizer+%@test.local'
                OR email LIKE 'attendee+%@test.local'
            )
        """)
    )
    await session.execute(
        text("""
            DELETE FROM event_attendees WHERE user_id IN (
                SELECT id FROM users WHERE email LIKE 'test+pw%@example.com'
                OR email LIKE 'organizer+%@test.local'
                OR email LIKE 'attendee+%@test.local'
            )
        """)
    )
    await session.execute(
        text("""
            DELETE FROM events WHERE owner_id IN (
                SELECT id FROM users WHERE email LIKE 'test+pw%@example.com'
                OR email LIKE 'organizer+%@test.local'
                OR email LIKE 'attendee+%@test.local'
            )
        """)
    )
    await session.execute(
        text("""
            DELETE FROM referrals WHERE user_id IN (
                SELECT id FROM users WHERE email LIKE 'test+pw%@example.com'
                OR email LIKE 'organizer+%@test.local'
                OR email LIKE 'attendee+%@test.local'
            )
        """)
    )
    await session.execute(
        text("""
            DELETE FROM users WHERE email LIKE 'test+pw%@example.com'
            OR email LIKE 'organizer+%@test.local'
            OR email LIKE 'attendee+%@test.local'
        """)
    )

    await session.commit()
    return {"message": "Test data cleaned up"}
