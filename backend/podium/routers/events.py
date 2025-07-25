import random
from fastapi import APIRouter, Path
from typing import Annotated, Union, List
from fastapi import Depends, HTTPException, Query
from fastapi_cache.decorator import cache
from podium.db.event import InternalEvent, PrivateEvent
from podium.db.vote import CreateVotes, VoteCreate
from pyairtable.formulas import match
from pydantic import BaseModel
from secrets import token_urlsafe


from requests import HTTPError

from podium.routers.auth import get_current_user
from podium.db.user import UserPrivate
from podium import db
from podium.db import (
    EventCreationPayload,
    EventUpdate,
    UserEvents,
    Event,
    ReferralBase,
)
from podium.db.project import Project
from podium.constants import AIRTABLE_NOT_FOUND_CODES, BAD_AUTH, BAD_ACCESS, Slug
from slugify import slugify

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/{event_id}")
def get_event(
    event_id: Annotated[str, Path(title="Event Airtable ID")],
    user: Annotated[UserPrivate, Depends(get_current_user)],
) -> Union[PrivateEvent, Event]:
    """
    Get an event by its ID. If the user owns it, return a PrivateEvent. Otherwise, return a regular event. Can be called with invalid auth credentials if needed, but will need something in the bearer token for the code to work
    """
    try:
        event = db.events.get(event_id)
    except HTTPError as e:
        raise (
            HTTPException(status_code=404, detail="Event not found")
            if e.response.status_code in AIRTABLE_NOT_FOUND_CODES
            else e
        )

    if user and user.id in event["fields"].get("owner", []):
        event = PrivateEvent.model_validate(event["fields"])
    else:
        event = Event.model_validate(event["fields"])

    return event


# Used to be /attending
@router.get("/")
def get_attending_events(
    user: Annotated[UserPrivate, Depends(get_current_user)],
) -> UserEvents:
    """
    Get a list of all events that the current user is attending.
    """
    if user is None:
        raise BAD_AUTH

    # Eventually it might be better to return a user object. Otherwise, the client that the event owner is using would need to fetch the user. Since user emails probably shouldn't be public with just a record ID as a parameter, we would need to check if the person calling GET /users?user=ID has an event wherein that user ID is present. To avoid all this, the user object could be returned.

    owned_events = [
        PrivateEvent.model_validate(event["fields"])
        for event in [db.events.get(event_id) for event_id in user.owned_events]
    ]
    attending_events = [
        Event.model_validate(event["fields"])
        for event in [db.events.get(event_id) for event_id in user.attending_events]
    ]

    return UserEvents(owned_events=owned_events, attending_events=attending_events)


@router.post("/")
def create_event(
    event: EventCreationPayload,
    user: Annotated[UserPrivate, Depends(get_current_user)],
):
    """
    Create a new event. The current user is automatically added as an owner of the event.
    """
    if user is None:
        raise BAD_AUTH
    owner = [user.id]

    # Turn the event name into a slug and check if it already exists. If the slug already exists, raise an error
    slug = slugify(event.name, lowercase=True, separator="-")
    if db.events.first(formula=match({"slug": slug})):
        raise HTTPException(
            status_code=400,
            detail="Event slug already exists. Please choose a different name. If you think this is an error, please contact us.",
        )

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
        slug=slug,
        id="",  # Placeholder to prevent an unnecessary class
    )
    db.events.create(full_event.model_dump(exclude={"id", "max_votes_per_user"}))[
        "fields"
    ]


@router.post("/attend")
def attend_event(
    join_code: Annotated[str, Query(description="A unique code used to join an event")],
    referral: Annotated[str, Query(description="How did you hear about this event?")],
    user: Annotated[UserPrivate, Depends(get_current_user)],
):
    """
    Attend an event. The client must supply a join code that matches the event's join code.
    """
    if user is None:
        raise BAD_AUTH

    # Get the first (and presumably only) event with the given join code
    event = db.events.first(formula=match({"join_code": join_code.upper()}))
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    event = PrivateEvent.model_validate(event["fields"])

    # If the event is found, add the current user to the attendees list
    # But first, ensure that the user is not already in the list
    if user.id in event.attendees:
        raise HTTPException(status_code=400, detail="User already attending event")
    db.events.update(
        event.id,
        {"attendees": event.attendees + [user.id]},
    )
    # Create a referral record if the referral is not empty
    if referral:
        db.referrals.create(
            ReferralBase(
                content=referral,
                event=[event.id],
                user=[user.id],
            ).model_dump()
        )


@router.put("/{event_id}")
def update_event(
    event_id: Annotated[str, Path(title="Event ID")],
    event: EventUpdate,
    user: Annotated[UserPrivate, Depends(get_current_user)],
):
    """
    Update event's information
    """
    # Check if the user is the owner of the event
    if user is None or event_id not in user.owned_events:
        # This also ensures the event exists since it has to exist to be in the user's owned events
        raise BAD_ACCESS

    db.events.update(event_id, event.model_dump())["fields"]


@router.delete("/{event_id}")
def delete_event(
    event_id: Annotated[str, Path(title="Event ID")],
    user: Annotated[UserPrivate, Depends(get_current_user)],
):
    # Check if the user is an owner of the event
    if user is None or event_id not in user.owned_events:
        raise BAD_ACCESS

    db.events.delete(event_id)


# Voting! The client should POST to /events/{event_id}/vote with their top 3 favorite projects, in no particular order. If there are less than 20 projects in the event, only accept the top 2
@router.post("/vote")
def vote(votes: CreateVotes, user: Annotated[UserPrivate, Depends(get_current_user)]):
    """
    Vote for the top 3 projects in an event. The client must provide the event ID and a list of the top 3 projects. If there are less than 20 projects in the event, only the top 2 projects are required.
    """

    try:
        event = db.events.get(votes.event)
        event = PrivateEvent.model_validate(event["fields"])
    except HTTPError as e:
        raise (
            HTTPException(status_code=404, detail="Event not found")
            if e.response.status_code in AIRTABLE_NOT_FOUND_CODES
            else e
        )

    # Check if the user is not None and is attending the event
    if user is None or user.id not in event.attendees:
        raise BAD_ACCESS

    for project_id in votes.projects:
        vote = VoteCreate(
            project=[project_id],
            event=[event.id],
            voter=[user.id],
        )
        try:
            project = db.projects.get(project_id)
        except HTTPError as e:
            if e.response.status_code in AIRTABLE_NOT_FOUND_CODES:
                raise HTTPException(status_code=404, detail="Project not found")
            else:
                raise e
        project = Project.model_validate(project["fields"])

        # Check if the project is in the event
        if project.event != [event.id]:
            raise HTTPException(status_code=400, detail="Project is not in the event")

        # fetch votes wherein the user is the voter and the event is the event_id. These need to be lookup fields, it seems
        formula = match({"user_id": user.id, "event_id": event.id})

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
                {"user_id": user.id, "event_id": event.id, "project_id": project.id}
            )
        ):
            raise HTTPException(
                status_code=400,
                detail="User has already voted for this project",
            )

        if user.id in project.collaborators or user.id in project.owner:
            raise HTTPException(
                status_code=403,
                detail="User cannot vote for their own project",
            )

        # Create vote record
        db.votes.create(vote.model_dump())


@router.get("/{event_id}/leaderboard")
def get_leaderboard(event_id: Annotated[str, Path(title="Event ID")]) -> List[Project]:
    """
    Return a sorted list of projects in the event
    """
    try:
        event = db.events.get(event_id)
    except HTTPError as e:
        raise (
            HTTPException(status_code=404, detail="Event not found")
            if e.response.status_code in AIRTABLE_NOT_FOUND_CODES
            else e
        )
    event = PrivateEvent.model_validate(event["fields"])
    if not event.leaderboard_enabled:
        raise HTTPException(
            status_code=403, detail="Leaderboard is not enabled for this event"
        )
    projects = []
    for project_id in event.projects:
        try:
            project = db.projects.get(project_id)
            projects.append(project)
        except HTTPError as e:
            if e.response.status_code in AIRTABLE_NOT_FOUND_CODES:
                print(
                    f"WARNING: Project {project_id} not found when getting leaderboard for event {event_id}"
                )
            else:
                raise e

    # Sort the projects by the number of votes they have received
    projects.sort(key=lambda project: project["fields"].get("points", 0), reverse=True)

    projects = [Project.model_validate(project["fields"]) for project in projects]
    return projects


@router.get("/{event_id}/projects")
@cache(expire=30, namespace="events")
async def get_event_projects(
    event_id: Annotated[str, Path(title="Event ID")],
) -> List[Project]:
    """
    Get the projects for a specific event in a random order
    """
    try:
        event = db.events.get(event_id)
    except HTTPError as e:
        raise (
            HTTPException(status_code=404, detail="Event not found")
            if e.response.status_code in AIRTABLE_NOT_FOUND_CODES
            else e
        )

    projects = [
        Project.model_validate(project["fields"])
        for project in [
            db.projects.get(project_id)
            for project_id in event["fields"].get("projects", [])
        ]
    ]
    random.shuffle(projects)
    return projects


@router.get("/id/{slug}")
@cache(expire=60, namespace="events")
async def get_at_id(
    slug: Annotated[Slug, Path(title="Event Slug")],
) -> str:
    """
    Get an event's Airtable ID by its slug.
    """
    # Query database
    event = db.events.first(formula=match({"slug": slug}))
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    event = InternalEvent.model_validate(event["fields"])
    
    return event.id
