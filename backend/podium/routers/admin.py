from fastapi import APIRouter, Body
from podium import db
from podium.constants import AIRTABLE_NOT_FOUND_CODES, BAD_ACCESS
from podium.db.event import PrivateEvent, InternalEvent
from podium.routers.auth import get_current_user
from fastapi import Depends, HTTPException, Path
from typing import Annotated, List
from podium.db.user import get_users_from_record_ids, UserAttendee, UserInternal
from podium.routers.auth import UserInternal
from requests import HTTPError
router = APIRouter(prefix="/events", tags=["events"])



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
            HTTPError(status_code=404, detail="Event not found")
            if e.response.status_code in AIRTABLE_NOT_FOUND_CODES
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