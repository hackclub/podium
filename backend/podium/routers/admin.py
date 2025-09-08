from fastapi import APIRouter, Body
from podium import db
from podium.constants import AIRTABLE_NOT_FOUND_CODES, BAD_ACCESS
from pyairtable.formulas import match
from podium.db.event import PrivateEvent, InternalEvent
from podium.routers.auth import get_current_user
from fastapi import Depends, HTTPException, Path
from typing import Annotated, List
from podium.db.user import get_users_from_record_ids, UserAttendee
from podium.routers.auth import UserInternal
from podium.db.project import Project
from podium.db.vote import Vote
from podium.db.referral import Referral
from podium.routers.events import get_projects_for_event
router = APIRouter(prefix="/events/admin", tags=["events"])



def is_user_event_owner(user: UserInternal, event_id: str) -> bool:
    return event_id in user.owned_events

@router.get("/{event_id}")
def get_event(
    event_id: Annotated[str, Path(title="Event ID")],
    user: Annotated[UserInternal, Depends(get_current_user)],
) -> PrivateEvent:
    if not is_user_event_owner(user, event_id):
        raise BAD_ACCESS
    try:
        event = PrivateEvent.model_validate(db.events.get(event_id)["fields"])
    except HTTPException as e:
        raise (
            HTTPException(status_code=404, detail="Event not found")
            if e.status_code in AIRTABLE_NOT_FOUND_CODES
            else e
        )
    return event


@router.get("/{event_id}/attendees")
def get_event_attendees(
    event_id: Annotated[str, Path(title="Event ID")],
    user: Annotated[UserInternal, Depends(get_current_user)],
) -> List[UserAttendee]:
    """Get the attendees of an event"""
    if not is_user_event_owner(user, event_id):
        raise BAD_ACCESS
    
    attendees = get_users_from_record_ids(db.events.get(event_id)["fields"].get("attendees", []), UserAttendee)
    return attendees

@router.post("/{event_id}/remove-attendee")
def remove_attendee(
    event_id: Annotated[str, Path(title="Event ID")],
    user_id: Annotated[str, Body(title="User ID")],
    user: Annotated[UserInternal, Depends(get_current_user)],
):
    if not is_user_event_owner(user, event_id):
        raise BAD_ACCESS
    db.events.update(event_id, {"attendees": [attendee for attendee in db.events.get(event_id)["fields"].get("attendees", []) if attendee != user_id]})
    return {"message": "Attendee removed"}


@router.get("/{event_id}/leaderboard", response_model=List[Project])
def get_event_leaderboard(
    event_id: Annotated[str, Path(title="Event ID")],
    user: Annotated[UserInternal, Depends(get_current_user)],
) -> List[Project]:
    """Get the leaderboard for an event (admin only)"""
    if not is_user_event_owner(user, event_id):
        raise BAD_ACCESS
    
    try:
        event = InternalEvent.model_validate(db.events.get(event_id)["fields"])
    except HTTPException as e:
        raise (
            HTTPException(status_code=404, detail="Event not found")
            if e.status_code in AIRTABLE_NOT_FOUND_CODES
            else e
        )
    
    # Get projects sorted by points (leaderboard order)
    return get_projects_for_event(event_id, shuffle=False, event=event)


@router.get("/{event_id}/votes")
def get_event_votes(
    event_id: Annotated[str, Path(title="Event ID")],
    user: Annotated[UserInternal, Depends(get_current_user)],
) -> List[Vote]:
    """Get all votes for an event (admin only)"""
    if not is_user_event_owner(user, event_id):
        raise BAD_ACCESS
    
    try:
        db.events.get(event_id)
    except HTTPException as e:
        raise (
            HTTPException(status_code=404, detail="Event not found")
            if e.status_code in AIRTABLE_NOT_FOUND_CODES
            else e
        )
    
    # Get all votes for this event
    formula = match({"event_id": event_id})
    votes = db.votes.all(formula=formula)
    return [Vote.model_validate(vote["fields"]) for vote in votes]


@router.get("/{event_id}/referrals")
def get_event_referrals(
    event_id: Annotated[str, Path(title="Event ID")],
    user: Annotated[UserInternal, Depends(get_current_user)],
) -> List[Referral]:
    """Get all referrals for an event (admin only)"""
    if not is_user_event_owner(user, event_id):
        raise BAD_ACCESS
    
    try:
        db.events.get(event_id)
    except HTTPException as e:
        raise (
            HTTPException(status_code=404, detail="Event not found")
            if e.status_code in AIRTABLE_NOT_FOUND_CODES
            else e
        )
    
    # Get all referrals for this event
    formula = match({"event_id": event_id})
    referrals = db.referrals.all(formula=formula)
    return [Referral.model_validate(referral["fields"]) for referral in referrals]