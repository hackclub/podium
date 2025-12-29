from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Path
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload

from podium.db.postgres import (
    User,
    Event,
    EventPrivate,
    Project,
    ProjectPrivate,
    Vote,
    Referral,
    get_session,
    scalar_one_or_none,
    scalar_all,
)
from podium.routers.auth import get_current_user
from podium.constants import BAD_ACCESS

router = APIRouter(prefix="/events/admin", tags=["events"])


class UserAttendee(BaseModel):
    id: UUID
    email: str
    display_name: str
    first_name: str
    last_name: str


class VoteResponse(BaseModel):
    id: UUID
    voter_id: UUID
    project_id: UUID
    event_id: UUID


class ReferralResponse(BaseModel):
    id: UUID
    content: str
    user_id: UUID
    event_id: UUID


async def get_owned_event(
    event_id: UUID, user: User, session: AsyncSession
) -> Event:
    """Get an event if the user owns it, else raise BAD_ACCESS."""
    event = await session.get(Event, event_id)
    if not event or event.owner_id != user.id:
        raise BAD_ACCESS
    return event


@router.get("/{event_id}")
async def get_event_admin(
    event_id: Annotated[UUID, Path(title="Event ID")],
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> EventPrivate:
    event = await get_owned_event(event_id, user, session)
    return EventPrivate.model_validate(event)


@router.get("/{event_id}/attendees")
async def get_event_attendees(
    event_id: Annotated[UUID, Path(title="Event ID")],
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[UserAttendee]:
    """Get attendees of an event."""
    await get_owned_event(event_id, user, session)

    stmt = (
        select(Event)
        .where(Event.id == event_id)
        .options(selectinload(Event.attendees))
    )
    event = await scalar_one_or_none(session, stmt)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return [
        UserAttendee(
            id=a.id,
            email=a.email,
            display_name=a.display_name,
            first_name=a.first_name,
            last_name=a.last_name,
        )
        for a in event.attendees
    ]


@router.post("/{event_id}/remove-attendee")
async def remove_attendee(
    event_id: Annotated[UUID, Path(title="Event ID")],
    user_id: Annotated[UUID, Body(embed=True)],
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Remove an attendee from an event."""
    await get_owned_event(event_id, user, session)

    stmt = (
        select(Event)
        .where(Event.id == event_id)
        .options(selectinload(Event.attendees))
    )
    event = await scalar_one_or_none(session, stmt)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    event.attendees = [a for a in event.attendees if a.id != user_id]
    await session.commit()
    return {"message": "Attendee removed"}


@router.get("/{event_id}/leaderboard", response_model=list[ProjectPrivate])
async def get_event_leaderboard(
    event_id: Annotated[UUID, Path(title="Event ID")],
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[ProjectPrivate]:
    """Get leaderboard for an event (admin only)."""
    await get_owned_event(event_id, user, session)

    projects = await scalar_all(
        session,
        select(Project).where(Project.event_id == event_id).order_by(Project.points.desc()),
    )
    return [ProjectPrivate.model_validate(p) for p in projects]


@router.get("/{event_id}/votes")
async def get_event_votes(
    event_id: Annotated[UUID, Path(title="Event ID")],
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[VoteResponse]:
    """Get all votes for an event (admin only)."""
    await get_owned_event(event_id, user, session)

    votes = await scalar_all(session, select(Vote).where(Vote.event_id == event_id))
    return [
        VoteResponse(id=v.id, voter_id=v.voter_id, project_id=v.project_id, event_id=v.event_id)
        for v in votes
    ]


@router.get("/{event_id}/referrals")
async def get_event_referrals(
    event_id: Annotated[UUID, Path(title="Event ID")],
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[ReferralResponse]:
    """Get all referrals for an event (admin only)."""
    await get_owned_event(event_id, user, session)

    referrals = await scalar_all(
        session, select(Referral).where(Referral.event_id == event_id)
    )
    return [
        ReferralResponse(id=r.id, content=r.content, user_id=r.user_id, event_id=r.event_id)
        for r in referrals
    ]
