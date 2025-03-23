from fastapi import APIRouter, Path
from typing import Annotated, Self, Set, Union, List
from fastapi import Depends, HTTPException, Query
from podium.db.event import PrivateEvent
from pyairtable.formulas import match
from pyairtable.api.types import RecordDict
from secrets import token_urlsafe

from pydantic import BaseModel, Field, model_validator
from pydantic.json_schema import SkipJsonSchema

from requests import HTTPError

from podium.routers.auth import get_current_user
from podium.db.user import CurrentUser, User
from podium import db
from podium.db import (
    EventCreationPayload,
    PrivateEvent,
    UserEvents,
    Event,
    ReferralBase,
)
from podium.db.project import Project

router = APIRouter(prefix="/events", tags=["events"])


# TODO: The only reason there is a different endpoint for an unauthenticated request to get an event is because Depends(get_current_user) will not return None if there is no token, it'll error
@router.get("/unauthenticated/{event_id}")
def get_event_unauthenticated(event_id: Annotated[str, Path(title="Event ID")]) -> Event:
    """
    Get an event by its ID. This is used for the public event page.
    """
    try:
        event = db.events.get(event_id)
    except HTTPError as e:
        raise (
                HTTPException(status_code=404, detail="Event not found")
                if e.response.status_code == 404
                else e
            )
    return Event.model_validate({"id": event["id"], **event["fields"]})

@router.get("/{event_id}")
def get_event(
    event_id: Annotated[str, Path(title="Event ID")],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> Union[PrivateEvent, Event]:
    """
    Get an event by its ID. If the user owns it, return a PrivateEvent. Otherwise, return a regular event.
    """

    user_id = db.user.get_user_record_id_by_email(current_user.email)
    if user_id is None:
        raise HTTPException(status_code=500, detail="User not found")

    user = db.users.get(user_id)

    try:
        event = db.events.get(event_id)
    except HTTPError as e:
        raise (
                HTTPException(status_code=404, detail="Event not found")
                if e.response.status_code == 404
                else e
            )

    if user["id"] in event["fields"].get("owner", []):
        return PrivateEvent.model_validate({"id": event["id"], **event["fields"]})
    elif user["id"] in event["fields"].get("attendees", []):
        return Event.model_validate({"id": event["id"], **event["fields"]})
    else:
        raise HTTPException(
            status_code=403, detail="User does not have access to event"
        )


# Used to be /attending
@router.get("/")
def get_attending_events(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> UserEvents:
    """
    Get a list of all events that the current user is attending.
    """
    user_id = db.user.get_user_record_id_by_email(current_user.email)
    if user_id is None:
        raise HTTPException(status_code=500, detail="User not found")
    user = db.users.get(user_id)

    # Eventually it might be better to return a user object. Otherwise, the client that the event owner is using would need to fetch the user. Since user emails probably shouldn't be public with just a record ID as a parameter, we would need to check if the person calling GET /users?user=ID has an event wherein that user ID is present. To avoid all this, the user object could be returned.
    
    owned_events = [
        PrivateEvent.model_validate({"id": event["id"], **event["fields"]})
        for event in [
            db.events.get(event_id)
            for event_id in user["fields"].get("owned_events", [])
        ]
    ]
    attending_events = [
        Event.model_validate({"id": event["id"], **event["fields"]})
        for event in [
            db.events.get(event_id)
            for event_id in db.users.get(user_id)["fields"].get("attending_events", [])
        ]
    ]

    return UserEvents(owned_events=owned_events, attending_events=attending_events)


@router.post("/")
def create_event(
    event: EventCreationPayload,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """
    Create a new event. The current user is automatically added as an owner of the event.
    """
    # No matter what email the user provides, the owner is always the current user
    owner = [db.user.get_user_record_id_by_email(current_user.email)]
    # If the owner is not found, return a 404. Since there might eventually be multiple owners, just check if any of them are None
    if None in owner:
        raise HTTPException(status_code=404, detail="User not found")

    # Generate a unique join code by continuously generating a new one until it doesn't match any existing join codes
    while True:
        join_code = token_urlsafe(3).upper()
        if not db.events.first(formula=match({"join_code": join_code})):
            join_code = join_code
            break

    # https://docs.pydantic.dev/latest/concepts/serialization/#model_copy
    full_event = PrivateEvent(
        **event.model_dump(),
        join_code=join_code,
        owner=owner,
        id="",  # Placeholder to prevent an unnecessary class
    )
    db.events.create(full_event.model_dump(exclude={"id"}))["fields"]

@router.post("/attend")
def attend_event(
    join_code: Annotated[str, Query(description="A unique code used to join an event")],
    referral: Annotated[str, Query(description="How did you hear about this event?")],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """
    Attend an event. The client must supply a join code that matches the event's join code.
    """
    user_id = db.user.get_user_record_id_by_email(current_user.email)
    if user_id is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Accomplish this by trying to match the join code against the table and if nothing matches, return a 404
    event = db.events.first(formula=match({"join_code": join_code.upper()}))
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    # If the event is found, add the current user to the attendees list
    # But first, ensure that the user is not already in the list
    if user_id in event["fields"].get("attendees", []):
        raise HTTPException(status_code=400, detail="User already attending event")
    db.events.update(
        event["id"],
        {"attendees": event["fields"].get("attendees", []) + [user_id]},
    )
    # Create a referral record
    db.referrals.create(
        ReferralBase(
            content=referral,
            event=[event["id"]],
            user=[user_id],
        ).model_dump()
    )


# Voting! The client should POST to /events/{event_id}/vote with their top 3 favorite projects, in no particular order. If there are less than 20 projects in the event, only accept the top 2


class Vote(BaseModel):
    # ... signifies that the field is required: https://docs.pydantic.dev/latest/concepts/models/#required-fields
    event_id: str = Field(..., description="The ID of the event to vote in.")
    # Sets prevent duplicates so they're perfect for this use case
    projects: Set[str] = Field(
        ...,
        min_items=2,
        max_items=3,
        title="Nominees",
        description="In no particular order, the top 3 (or 2 if there are less than 20 projects) projects that the user is voting for.",
    )
    event: SkipJsonSchema[RecordDict] = None

    # ~~Putting this in kwargs instead so Swagger doesn't show it~~ shows `"additionalProp1":{}` for some reason
    # https://docs.pydantic.dev/latest/api/config/#pydantic.config.ConfigDict.extra
    # model_config: SkipJsonSchema[ConfigDict] = ConfigDict(extra="allow")

    @model_validator(mode="after")
    def validate_projects(self) -> Self:
        try:
            # TODO: Validate event via Pydantic
            self.event = db.events.get(self.event_id)
        except HTTPError as e:
            raise (
                HTTPException(status_code=404, detail="Event not found")
                if e.response.status_code == 404
                else e
            )
        
        if not self.event["fields"].get("votable", False):
            raise HTTPException(status_code=400, detail="Event is not votable yet")
        
        if len(self.projects) < 2:
            raise HTTPException(
                status_code=400, detail="At least 2 projects are required"
            )
        
        
        if len(self.projects) < 3 and len(self.event["fields"]["projects"]) >= 20:
            raise HTTPException(
                status_code=400,
                detail="3 nominations are required for events with 20 or more projects",
            )
        elif len(self.projects) > 2 and len(self.event["fields"]["projects"]) < 20:
            raise HTTPException(
                status_code=400,
                detail="Only 2 nominations are allowed for events with less than 20 projects",
            )
        if len(self.projects) > 3:
            raise HTTPException(
                status_code=400, detail="At most 3 projects are allowed"
            )

        # Ensure that the projects exist, they match the event, and the string starts with 'rec'
        for project_id in self.projects:
            try:
                project = db.projects.get(project_id)
            except HTTPError as e:
                raise (
                    HTTPException(status_code=404, detail="Project not found")
                    if e.response.status_code == 404
                    else e
                )
            if project["fields"]["event"][0] != self.event_id:
                raise HTTPException(
                    status_code=400, detail="Project does not belong to event"
                )
        return self


@router.put("/{event_id}/change-votable/")
def change_votable(
    event_id: Annotated[str, Path(title="Event ID")],
    votable: Annotated[bool, Query(description="Whether the event is votable or not")],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """
    Change event's votable state. Toogled votable status means that users can vote for their favorite projects in the event.
    """
    user_id = db.user.get_user_record_id_by_email(current_user.email)
    if user_id is None:
        raise HTTPException(status_code=404, detail="User not found")
    user = db.users.get(user_id)
    user = User.model_validate({"id": user["id"], **user["fields"]})
    # Check if the user is the owner of the event
    if event_id not in user.owned_events:
        # This also ensures the event exists since it has to exist to be in the user's owned events
        raise HTTPException(status_code=403, detail="User is not an owner of the event")

    db.events.update(event_id, {"votable": votable})
    return {"status": "success", "event_id": event_id}


# @router.post("/{event_id}/vote")
@router.post("/vote")
def vote(vote: Vote, current_user: Annotated[CurrentUser, Depends(get_current_user)]):
    """
    Vote for the top 3 projects in an event. The client must provide the event ID and a list of the top 3 projects. If there are less than 20 projects in the event, only the top 2 projects are required.
    """

    user_id = db.user.get_user_record_id_by_email(current_user.email)
    if user_id is None:
        raise HTTPException(status_code=404, detail="User not found")
    user = db.users.get(user_id)

    if vote.event_id in user["fields"].get("votes", []):
        raise HTTPException(status_code=400, detail="User has already voted in event")

    # Check if they're an attendee of the event
    if vote.event_id not in user["fields"].get("attending_events", []):
        raise HTTPException(status_code=403, detail="User is not attending event")

    # Update the user's votes
    db.users.update(
        user["id"],
        {
            "votes": user["fields"].get("votes", []) + [vote.event_id],
        },
    )
    # Fetch the user again so we can remove the event ID if we need to
    user_id = db.user.get_user_record_id_by_email(current_user.email)
    user = db.users.get(user_id)
    
    # Check if the user is trying to vote for their own project(s) or if a project doesn't exist
    projects = []
    for project_id in vote.projects:
        # Frankly, this try-except block is a bit redundant since the model_validator should catch it
        try:
            # Get the project record
            project = db.projects.get(project_id)
            # Appending to a list so it can be used later without needing to fetch the project again
            projects.append(project)
            # Check if the user is the owner and raise an error if they are
            if user_id in project["fields"].get("owner", []) or user_id in project["fields"].get("collaborators", []):
                # Unmark user as voted if they are the owner of the project and it's oging to error
                user_votes = user["fields"].get("votes", [])
                # Remove the event ID from the user's votes
                user_votes.remove(vote.event_id)
                # Update the user's votes
                db.users.update(
                    user["id"],
                    {
                        "votes": user_votes,
                    },
                )
                raise HTTPException(
                    status_code=400, detail="User cannot vote for their own project"
                )
        except HTTPError as e:
            # Unmark user as voted if something goes wrong
            user_votes = user["fields"].get("votes", [])
            # Remove the event ID from the user's votes
            user_votes.remove(vote.event_id)
            # Update the user's votes
            db.users.update(
                user["id"],
                {
                    "votes": user_votes,
                },
            )
            raise (
                HTTPException(status_code=404, detail="Project not found")
                if e.response.status_code == 404
                else e
            )

    # Update the votes (increment the `points` field of the nominated projects by 1)
    for project in projects:
        # Increment the points field by 1
        db.projects.update(
            project["id"], {"points": project["fields"].get("points", 0) + 1}
        )



@router.get("/{event_id}/leaderboard")
def get_leaderboard(event_id: Annotated[str, Path(title="Event ID")]) -> List[Project]:
    """
    Get the leaderboard for an event. The leaderboard is a list of projects in the event, sorted by the number of votes they have received.
    """
    try:
        event = db.events.get(event_id)
    except HTTPError as e:
        raise (
                HTTPException(status_code=404, detail="Event not found")
                if e.response.status_code == 404
                else e
            )
    projects = []
    for project_id in event["fields"].get("projects", []):
        try:
            project = db.projects.get(project_id)
            projects.append(project)
        except HTTPError as e:
            if e.response.status_code == 404:
                print(
                    f"WARNING: Project {project_id} not found when getting leaderboard for event {event_id}"
                )
            else:
                raise e

    # Sort the projects by the number of votes they have received
    projects.sort(key=lambda project: project["fields"].get("points", 0), reverse=True)

    projects = [
        Project.model_validate({"id": project["id"], **project["fields"]})
        for project in projects
    ]
    return projects


@router.get("/{event_id}/projects")
def get_event_projects(
    event_id: Annotated[str, Path(title="Event ID")],
) -> List[Project]:
    """
    Get the projects for a specific event.
    """
    try:
        event = db.events.get(event_id)
    except HTTPError as e:
        raise (
            HTTPException(status_code=404, detail="Event not found")
            if e.response.status_code == 404
            else e
        )

    projects = [
        Project.model_validate({"id": project["id"], **project["fields"]})
        for project in [
            db.projects.get(project_id)
            for project_id in event["fields"].get("projects", [])
        ]
    ]
    return projects
