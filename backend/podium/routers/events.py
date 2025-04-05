from fastapi import APIRouter, Path
from typing import Annotated, Union, List
from fastapi import Depends, HTTPException, Query
from podium.db.event import PrivateEvent
from podium.db.vote import CreateVotes, VoteCreate
from pyairtable.formulas import match

from secrets import token_urlsafe


from requests import HTTPError

from podium.routers.auth import get_current_user
from podium.db.user import CurrentUser, User
from podium import db
from podium.db import (
    EventCreationPayload,
    EventUpdate,
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
                if e.response.status_code in [404, 403]
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
                if e.response.status_code in [404, 403]
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
        raise HTTPException(status_code=400, detail="User not found")
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
    db.events.create(full_event.model_dump(exclude={"id", "max_votes_per_user"}))["fields"]

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




@router.put("/{event_id}")
def update_event(
    event_id: Annotated[str, Path(title="Event ID")],
    event: EventUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """
    Update event's information
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

    return db.events.update(event_id, event.model_dump())["fields"]


@router.delete("/{event_id}")
def delete_event(
    event_id: Annotated[str, Path(title="Event ID")],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    # Check if the user is an owner of the event
    user_id = db.user.get_user_record_id_by_email(current_user.email)
    user = db.users.get(user_id)
    user = User.model_validate({"id": user["id"], **user["fields"]})
    # Check if the user is the owner of the event
    if event_id not in user.owned_events:
        raise HTTPException(status_code=403, detail="User not an owner of the event")

    return db.events.delete(event_id)


# Voting! The client should POST to /events/{event_id}/vote with their top 3 favorite projects, in no particular order. If there are less than 20 projects in the event, only accept the top 2
@router.post("/vote")
def vote(votes: CreateVotes, current_user: Annotated[CurrentUser, Depends(get_current_user)]):
    """
    Vote for the top 3 projects in an event. The client must provide the event ID and a list of the top 3 projects. If there are less than 20 projects in the event, only the top 2 projects are required.
    """

    user_id = db.user.get_user_record_id_by_email(current_user.email)
    if user_id is None: 
        raise HTTPException(status_code=404, detail="User not found")
    user = db.users.get(user_id)
    user = User.model_validate({"id": user["id"], **user["fields"]})
    try:
        event = db.events.get(votes.event)
        event = PrivateEvent.model_validate({"id": event["id"], **event["fields"]})
    except HTTPError as e:
        raise (
            HTTPException(status_code=404, detail="Event not found")
            if e.response.status_code in [404, 403]
            else e
        )

    # Check if the user is attending the event ( since user is authenticated but not attending the event )
    if user_id not in event.attendees:
        raise HTTPException(status_code=403, detail="User is not attending the event")

    for project_id in votes.projects:
        vote = VoteCreate(
            project=[project_id],
            event=[event.id],
            voter=[user_id],
        )
        try:
            project = db.projects.get(project_id)
        except HTTPError as e:
            if e.response.status_code in [404, 403]:
                raise HTTPException(status_code=404, detail="Project not found")
            else:
                raise e
        project = Project.model_validate({"id": project["id"], **project["fields"]})

        # Check if the project is in the event
        if project.event != [event.id]:
            raise HTTPException(
                status_code=400, detail="Project is not in the event"
            )

        # fetch votes wherein the user is the voter and the event is the event_id. These need to be lookup fields, it seems
        formula = match(
            {"user_id": user_id, "event_id": event.id}
        )
            
        existing_votes = db.votes.all(formula=formula)
        # Check if the user has already met the required number of votes
        if len(existing_votes) >= event.max_votes_per_user:
            raise HTTPException(
                status_code=400,
                detail=f"User has already voted for {event.max_votes_per_user} projects",
            )
        
        # Check if the user has already voted for this project
        if db.votes.all(
            formula=match(
                {"user_id": user_id, "event_id": event.id, "project_id": project.id}
            )
        ):
            raise HTTPException(
                status_code=400,
                detail="User has already voted for this project",
            )
        
        if user_id in project.collaborators or user_id in project.owner:
            raise HTTPException(
                status_code=403,
                detail="User cannot vote for their own project",
            )
        
        # Create vote record
        db.votes.create(vote.model_dump())
            

            

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
                if e.response.status_code in [404, 403]
                else e
            )
    projects = []
    for project_id in event["fields"].get("projects", []):
        try:
            project = db.projects.get(project_id)
            projects.append(project)
        except HTTPError as e:
            if e.response.status_code in [404, 403]:
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
            if e.response.status_code in [404, 403]
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