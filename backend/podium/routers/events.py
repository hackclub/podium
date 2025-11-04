import random
from secrets import token_urlsafe
from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pyairtable.formulas import match
from slugify import slugify
from podium.routers.auth import get_current_user
from podium.db.user import UserInternal
from podium import db
from podium.db import (
    EventCreationPayload,
    EventUpdate,
    UserEvents,
    Event,
    ReferralBase,
)
from podium.db.event import PrivateEvent
from podium.db.vote import CreateVotes, VoteCreate
from podium.db.project import Project
from podium.constants import BAD_AUTH, BAD_ACCESS, Slug
from podium.cache.operations import (
    get_event,
    get_event_by_slug,
    get_events_by_ids,
    get_events_by_owner,
    get_projects_for_event,
    get_project,
    invalidate_event,
    upsert_event,
)

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/{event_id}")
def get_event_endpoint(
    event_id: Annotated[str, Path(title="Event Airtable ID")],
) -> Event:
    """
    Get a public event by its ID. For admin features, use the admin endpoints.
    """
    # Use cache-first lookup
    event = get_event(event_id, model=Event)
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    return event


# Used to be /attending
@router.get("/")
def get_attending_events(
    user: Annotated[UserInternal, Depends(get_current_user)],
) -> UserEvents:
    """
    Get a list of all events that the current user is attending.
    """
    if user is None:
        raise BAD_AUTH

    # Eventually it might be better to return a user object. Otherwise, the client that the event owner is using would need to fetch the user. Since user emails probably shouldn't be public with just a record ID as a parameter, we would need to check if the person calling GET /users?user=ID has an event wherein that user ID is present. To avoid all this, the user object could be returned.

    # Batch fetch owned events - try indexed query first, fall back to batch-by-IDs
    owned_events = get_events_by_owner(user.id, model=PrivateEvent)
    if not owned_events and user.owned_events:
        owned_events = get_events_by_ids(user.owned_events, model=PrivateEvent)
    
    # Batch fetch attending events - single Airtable query for all missing IDs
    attending_events = get_events_by_ids(user.attending_events, model=Event)

    return UserEvents(owned_events=owned_events, attending_events=attending_events)


@router.post("/")
def create_event(
    event: EventCreationPayload,
    user: Annotated[UserInternal, Depends(get_current_user)],
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
    created = db.events.create(
        full_event.model_dump(
            exclude={"id", "max_votes_per_user", "owned", "feature_flags_list"}
        )
    )
    # Upsert to cache for immediate availability
    created_event = PrivateEvent.model_validate({**created["fields"], "id": created["id"]})
    upsert_event(created_event)


@router.post("/attend")
def attend_event(
    join_code: Annotated[str, Query(description="A unique code used to join an event")],
    referral: Annotated[str, Query(description="How did you hear about this event?")],
    user: Annotated[UserInternal, Depends(get_current_user)],
):
    """
    Attend an event. The client must supply a join code that matches the event's join code.
    """
    if user is None:
        raise BAD_AUTH

    # Get the first (and presumably only) event with the given join code
    event_rec = db.events.first(formula=match({"join_code": join_code.upper()}))
    if event_rec is None:
        raise HTTPException(status_code=404, detail="Event not found")
    event = PrivateEvent.model_validate({**event_rec["fields"], "id": event_rec["id"]})

    # If the event is found, add the current user to the attendees list
    # But first, ensure that the user is not already in the list
    if user.id in event.attendees:
        raise HTTPException(status_code=400, detail="User already attending event")
    db.events.update(
        event.id,
        {"attendees": event.attendees + [user.id]},
    )
    # Invalidate cache so next read sees updated attendees
    invalidate_event(event.id)
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
    user: Annotated[UserInternal, Depends(get_current_user)],
):
    """
    Update event's information
    """
    # Check if the user is the owner of the event
    if user is None or event_id not in user.owned_events:
        # This also ensures the event exists since it has to exist to be in the user's owned events
        raise BAD_ACCESS

    db.events.update(event_id, event.model_dump())
    # Invalidate cache so next read sees updated event
    invalidate_event(event_id)


@router.delete("/{event_id}")
def delete_event(
    event_id: Annotated[str, Path(title="Event ID")],
    user: Annotated[UserInternal, Depends(get_current_user)],
):
    # Check if the user is an owner of the event
    if user is None or event_id not in user.owned_events:
        raise BAD_ACCESS

    db.events.delete(event_id)
    # Invalidate cache after deletion
    invalidate_event(event_id)


# Voting! The client should POST to /events/{event_id}/vote with their top 3 favorite projects, in no particular order. If there are less than 20 projects in the event, only accept the top 2
@router.post("/vote")
def vote(votes: CreateVotes, user: Annotated[UserInternal, Depends(get_current_user)]):
    """
    Vote for the top 3 projects in an event. The client must provide the event ID and a list of the top 3 projects. If there are less than 20 projects in the event, only the top 2 projects are required.
    """

    event = get_event(votes.event, model=PrivateEvent)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Check if the user is not None and is attending the event
    if user is None or user.id not in event.attendees:
        raise BAD_ACCESS

    for project_id in votes.projects:
        vote = VoteCreate(
            project=[project_id],
            event=[event.id],
            voter=[user.id],
        )
        project = get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

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





# The reason we're specifying response_model here is because of https://github.com/long2ice/fastapi-cache/issues/384
@router.get("/{event_id}/projects", response_model=List[Project])
async def get_event_projects(
    event_id: Annotated[str, Path(title="Event ID")],
    leaderboard: Annotated[
        bool,
        Query(
            title="Leaderboard",
            description="If true, and the event has a leaderboard enabled, the projects will be returned in order of points. Otherwise, they will be returned in random order",
        ),
    ],
) -> List[Project]:
    """
    Get the projects for a specific event
    """
    # Use cache-first lookup for projects
    if leaderboard:
        # Verify event exists and has leaderboard enabled
        event = get_event(event_id, model=PrivateEvent)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        if not event.leaderboard_enabled:
            raise HTTPException(
                status_code=403, detail="Leaderboard is not enabled for this event"
            )
        # Return sorted by points (cache handles sorting)
        return get_projects_for_event(event_id, sort_by_points=True)
    else:
        # Return in random order
        projects = get_projects_for_event(event_id, sort_by_points=False)
        random.shuffle(projects)
        return projects


# The reason we're specifying response_model here is because of https://github.com/long2ice/fastapi-cache/issues/384
@router.get("/id/{slug}", response_model=str)
async def get_at_id(
    slug: Annotated[Slug, Path(title="Event Slug")],
) -> str:
    """
    Get an event's Airtable ID by its slug.
    """
    # Use cache-first slug lookup
    event = get_event_by_slug(slug, model=Event)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return event.id
