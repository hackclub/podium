from fastapi import APIRouter, Body, Depends, HTTPException, Path
from typing import Annotated, List
from podium import db
from podium.constants import BAD_ACCESS
from podium.db.event import PrivateEvent
from podium.routers.auth import get_current_user
from podium.db.user import UserAttendee, UserInternal
from podium.cache.operations import get_user, get_projects_for_event, get_event, get_votes_for_event, get_referrals_for_event
from podium.db.project import AdminProject
from podium.db.vote import Vote
from podium.db.referral import Referral

router = APIRouter(prefix="/events/admin", tags=["events"])


def is_user_event_owner(user: UserInternal, event_id: str) -> bool:
    return event_id in user.owned_events


@router.get("/{event_id}")
def get_event_admin(
    event_id: Annotated[str, Path(title="Event ID")],
    user: Annotated[UserInternal, Depends(get_current_user)],
) -> PrivateEvent:
    if not is_user_event_owner(user, event_id):
        raise BAD_ACCESS
    event = get_event(event_id, model=PrivateEvent)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.get("/{event_id}/attendees")
def get_event_attendees(
    event_id: Annotated[str, Path(title="Event ID")],
    user: Annotated[UserInternal, Depends(get_current_user)],
) -> List[UserAttendee]:
    """Get the attendees of an event"""
    if not is_user_event_owner(user, event_id):
        raise BAD_ACCESS

    # Fetch attendees from cache
    event = get_event(event_id, model=PrivateEvent)
    attendee_ids = event.attendees if event else []
    attendees = [get_user(user_id, model=UserAttendee) for user_id in attendee_ids]
    return [a for a in attendees if a is not None]


@router.post("/{event_id}/remove-attendee")
def remove_attendee(
    event_id: Annotated[str, Path(title="Event ID")],
    user_id: Annotated[str, Body(title="User ID")],
    user: Annotated[UserInternal, Depends(get_current_user)],
):
    if not is_user_event_owner(user, event_id):
        raise BAD_ACCESS
    db.events.update(
        event_id,
        {
            "attendees": [
                attendee
                for attendee in db.events.get(event_id)["fields"].get("attendees", [])
                if attendee != user_id
            ]
        },
    )
    return {"message": "Attendee removed"}


@router.get(
    "/{event_id}/leaderboard", response_model=List[AdminProject]
)  # response model isn't needed here since we're not using fastapi-cache
def get_event_leaderboard(
    event_id: Annotated[str, Path(title="Event ID")],
    user: Annotated[UserInternal, Depends(get_current_user)],
) -> List[AdminProject]:
    """Get the leaderboard for an event (admin only)"""
    if not is_user_event_owner(user, event_id):
        raise BAD_ACCESS

    event = get_event(event_id, model=PrivateEvent)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Get projects sorted by points (leaderboard order) with AdminProject model
    return get_projects_for_event(event_id, sort_by_points=True, model=AdminProject)


@router.get("/{event_id}/votes")
def get_event_votes(
    event_id: Annotated[str, Path(title="Event ID")],
    user: Annotated[UserInternal, Depends(get_current_user)],
) -> List[Vote]:
    """Get all votes for an event (admin only)"""
    if not is_user_event_owner(user, event_id):
        raise BAD_ACCESS

    event = get_event(event_id, model=PrivateEvent)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Get all votes for this event
    votes = get_votes_for_event(event_id)
    return votes


@router.get("/{event_id}/referrals")
def get_event_referrals(
    event_id: Annotated[str, Path(title="Event ID")],
    user: Annotated[UserInternal, Depends(get_current_user)],
) -> List[Referral]:
    """Get all referrals for an event (admin only)"""
    if not is_user_event_owner(user, event_id):
        raise BAD_ACCESS

    event = get_event(event_id, model=PrivateEvent)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Get all referrals for this event
    referrals = get_referrals_for_event(event_id)
    return referrals
