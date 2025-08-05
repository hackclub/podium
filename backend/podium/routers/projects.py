from secrets import token_urlsafe
from typing import Annotated
from podium import settings
from requests import HTTPError
from podium import db
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pyairtable.formulas import EQ, RECORD_ID, match
from podium.routers.auth import get_current_user
from podium.db.user import UserPrivate
from podium.db.project import (
    InternalProject,
    PrivateProject,
    Project,
    PublicProjectCreationPayload,
)
from podium.generated.review_factory_models import Project as ReviewFactoryProject, Result as ReviewFactoryResult
from podium.db.project import ReviewFactoryClient
from podium.constants import AIRTABLE_NOT_FOUND_CODES, BAD_AUTH, BAD_ACCESS, EmptyModel

router = APIRouter(prefix="/projects", tags=["projects"])


# Get the current user's projects
@router.get("/mine")
def get_projects(
    user: Annotated[UserPrivate, Depends(get_current_user)],
) -> list[PrivateProject]:
    """
    Get the current user's projects and projects they are collaborating on.
    """

    if user is None:
        raise BAD_AUTH

    projects = [
        PrivateProject.model_validate(project["fields"])
        for project in [db.projects.get(project_id) for project_id in user.projects]
        + [db.projects.get(project_id) for project_id in user.collaborations]
    ]
    return projects


# It's up to the client to provide the event record ID
@router.post("/")
def create_project(
    project: PublicProjectCreationPayload,
    user: Annotated[UserPrivate, Depends(get_current_user)],
):
    """
    Create a new project. The current user is automatically added as an owner of the project.
    """
    if user is None:
        raise BAD_AUTH
    owner = [user.id]

    # Fetch all events that have a record ID matching the project's event ID
    records = db.events.all(formula=EQ(RECORD_ID(), project.event[0]))
    if not records:
        # If the event does not exist, raise a 404
        raise HTTPException(status_code=404, detail="Event not found")

    # If the owner is not part of the event that the project is going to be associated with, raise a 403
    # Might be good to put a try/except block here to check for a 404 but shouldn't be necessary as the event isn't user-provided, it's in the DB
    # TODO: replace with pydantic model
    event_attendees = db.events.get(project.event[0])["fields"].get("attendees", [])
    if not any(i in event_attendees for i in owner):
        raise HTTPException(status_code=403, detail="Owner not part of event")

    while True:
        join_code = token_urlsafe(3).upper()
        if not db.projects.first(formula=match({"join_code": join_code})):
            break

    # https://docs.pydantic.dev/latest/concepts/serialization/#model_copy
    full_project = InternalProject(
        **project.model_dump(),
        join_code=join_code,
        owner=owner,
        id="",  # Placeholder to prevent an unnecessary class
    )
    db.projects.create(
        full_project.model_dump(exclude={"id", "points", "cached_auto_quality"})
    )["fields"]


@router.post("/join")
def join_project(
    join_code: Annotated[
        str, Query(description="A unique code used to join a project as a collaborator")
    ],
    user: Annotated[UserPrivate, Depends(get_current_user)],
):
    if user is None:
        raise BAD_AUTH

    project = db.projects.first(formula=match({"join_code": join_code.upper()}))
    if project is None:
        raise HTTPException(status_code=404, detail="No project found")

    project = Project.model_validate(project["fields"])

    # Ensure the user isn't already a collaborator
    if user.id in project.collaborators or user.id in project.owner:
        raise HTTPException(
            status_code=400,
            detail="User is already a collaborator or owner of the project",
        )

    # Ensure the user is part of the event that the project is associated with
    # TODO: replace with pydantic model
    event_attendees = db.events.get(project.event[0])["fields"].get("attendees", [])
    if user.id not in event_attendees:
        raise BAD_ACCESS

    db.projects.update(project.id, {"collaborators": project.collaborators + [user.id]})


# Update project
@router.put("/{project_id}")
def update_project(
    project_id: Annotated[str, Path(pattern=r"^rec\w*$")],
    project: db.ProjectUpdate,
    user: Annotated[UserPrivate, Depends(get_current_user)],
):
    """
    Update a project by replacing it
    """
    # Check if the user is an owner of the project or if they even exist
    if user is None or user.id not in db.projects.get(project_id)["fields"].get(
        "owner", []
    ):
        raise BAD_ACCESS

    return db.projects.update(project_id, project.model_dump())["fields"]


# Delete project
@router.delete("/{project_id}")
def delete_project(
    project_id: Annotated[str, Path(pattern=r"^rec\w*$")],
    user: Annotated[UserPrivate, Depends(get_current_user)],
):
    # Check if the user is an owner of the project or if they even exist
    if user is None or user.id not in db.projects.get(project_id)["fields"].get(
        "owner", []
    ):
        raise BAD_ACCESS

    return db.projects.delete(project_id)


@router.get("/{project_id}")
# The regex here is to ensure that the path parameter starts with "rec" and is followed by any number of alphanumeric characters
def get_project(project_id: Annotated[str, Path(pattern=r"^rec\w*$")]):
    try:
        project = db.projects.get(project_id)
    except HTTPError as e:
        raise (
            HTTPException(status_code=404, detail="Project not found")
            if e.response.status_code in AIRTABLE_NOT_FOUND_CODES
            else e
        )
    return Project.model_validate(project["fields"])



@router.post("/check")
async def check_project(project: Project) -> ReviewFactoryResult:
    # TODO: add a parameter to force a recheck or request human review. This could just trigger a Slack webhook

    # Check if the review factory token is set, and if it isn't, return a 500 error
    if not settings.review_factory_token:
        raise HTTPException(status_code=500, detail="Review Factory token not set on backend")


    # Only check if the project exists in the DB
    try:
        # Don't trust the user to provide accurate cached_auto_quality data
        project = InternalProject.model_validate(db.projects.get(project.id)["fields"])
    except HTTPError as e:
        if e.response.status_code not in AIRTABLE_NOT_FOUND_CODES:
            raise e
        raise HTTPException(status_code=404, detail="Project not found")

    # Get the event to check if demo links are optional. Does not matter right now, as Review Factory doesn't support changing requirements, so keeping it commented out.
    # try:
        # event = InternalEvent.model_validate(db.events.get(project.event[0]))
    # except HTTPError:
        # raise HTTPException(status_code=404, detail="Event not found")

    # Check if what was before is the same as what we have now. Might be better to replace with proper caching later
    if not isinstance(project.cached_auto_quality, EmptyModel):
        if (
            (project.cached_auto_quality.repo == project.repo)
            and (project.cached_auto_quality.demo == project.demo)
            and (project.cached_auto_quality.image_url == project.image_url)
        ):
            # If it's all the same, return the cached stuff
            return project.cached_auto_quality
            
    # Recheck the project and update cached data
    client = ReviewFactoryClient(
        base_url=settings.review_factory_url,
        token=settings.review_factory_token,
    )
    # Convert our Project to ReviewFactoryProject format
    review_factory_project = ReviewFactoryProject(
        repo=str(project.repo),
        demo=str(project.demo),
    )
    project.cached_auto_quality = await client.check_project(review_factory_project)
    db.projects.update(
        project.id,
        {"cached_auto_quality": project.cached_auto_quality.model_dump_json()},
    )
    return project.cached_auto_quality

