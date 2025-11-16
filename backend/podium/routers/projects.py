from secrets import token_urlsafe
from typing import Annotated
from datetime import datetime
import httpx
from podium import settings, db, cache
from podium.cache.operations import Entity
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pyairtable.formulas import match
from podium.routers.auth import get_current_user
from podium.db.user import UserInternal
from podium.db.project import (
    InternalProject,
    PrivateProject,
    Project,
    ProjectCreationPayload,
    validate_demo_field,
)
from podium.db.event import PrivateEvent
from podium.generated.review_factory_models import CheckStatus
from podium.constants import BAD_AUTH, BAD_ACCESS, EmptyModel

router = APIRouter(prefix="/projects", tags=["projects"])


# Get the current user's projects
@router.get("/mine")
async def get_projects(
    user: Annotated[UserInternal, Depends(get_current_user)],
) -> list[PrivateProject]:
    """
    Get the current user's projects and projects they are collaborating on.
    """

    if user is None:
        raise BAD_AUTH

    # Combine owned and collaborated project IDs
    all_project_ids = user.projects + user.collaborations
    # Fetch projects from cache using PrivateProject model for join_code
    import asyncio
    projects = await asyncio.gather(*[cache.get_one(Entity.PROJECTS, project_id, PrivateProject) for project_id in all_project_ids])
    return [p for p in projects if p is not None]


# It's up to the client to provide the event record ID
@router.post("/")
async def create_project(
    project: ProjectCreationPayload,
    user: Annotated[UserInternal, Depends(get_current_user)],
):
    """
    Create a new project. The current user is automatically added as an owner of the project.
    """
    if user is None:
        raise BAD_AUTH
    owner = [user.id]

    # Fetch the event to validate demo field and check attendees (cache-first)
    event = await cache.get_one(Entity.EVENTS, project.event[0], PrivateEvent)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Validate demo field based on event's demo_links_optional setting
    validate_demo_field(project, event)

    # Ensure owner is in attendees (tolerate eventual consistency with retries)
    if user.id not in event.attendees:
        import asyncio
        for _ in range(10):
            await asyncio.sleep(0.1)
            refreshed = await cache.get_one(Entity.EVENTS, project.event[0], PrivateEvent)
            if refreshed and user.id in refreshed.attendees:
                event = refreshed
                break
        else:
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
    created = db.projects.create(
        full_project.model_dump(exclude={"id", "points", "cached_auto_quality", "collaborator_display_names", "owner_display_name"})
    )
    # Upsert to cache for immediate availability
    created_project = Project.model_validate({**created["fields"], "id": created["id"]})
    await cache.upsert_entity(Entity.PROJECTS, created_project)
    # Invalidate user cache since projects will be updated by Airtable
    # This ensures immediate consistency without waiting for webhook
    await cache.invalidate_entity(Entity.USERS, user.id)


@router.post("/join")
async def join_project(
    join_code: Annotated[
        str, Query(description="A unique code used to join a project as a collaborator")
    ],
    user: Annotated[UserInternal, Depends(get_current_user)],
):
    if user is None:
        raise BAD_AUTH

    project_rec = db.projects.first(formula=match({"join_code": join_code.upper()}))
    if project_rec is None:
        raise HTTPException(status_code=404, detail="No project found")

    project = Project.model_validate({**project_rec["fields"], "id": project_rec["id"]})

    # Ensure the user isn't already a collaborator
    if user.id in project.collaborators or user.id in project.owner:
        raise HTTPException(
            status_code=400,
            detail="User is already a collaborator or owner of the project",
        )

    # Ensure the user is part of the event that the project is associated with
    event = await cache.get_one(Entity.EVENTS, project.event[0], PrivateEvent)
    event_attendees = event.attendees if event else []
    if user.id not in event_attendees:
        raise BAD_ACCESS

    updated_collaborators = project.collaborators + [user.id]
    db.projects.update(project.id, {"collaborators": updated_collaborators})
    # Optimistically upsert updated project to cache to avoid stale reads
    updated_project = Project.model_validate({**project.model_dump(), "collaborators": updated_collaborators})
    await cache.upsert_entity(Entity.PROJECTS, updated_project)
    # Invalidate user cache since collaborations will be updated by Airtable
    # This ensures immediate consistency without waiting for webhook
    await cache.invalidate_entity(Entity.USERS, user.id)


# Update project
@router.put("/{project_id}")
async def update_project(
    project_id: Annotated[str, Path(pattern=r"^rec\w*$")],
    project: db.ProjectUpdate,
    user: Annotated[UserInternal, Depends(get_current_user)],
):
    """
    Update a project by replacing it
    """
    # Check if the user is an owner of the project or if they even exist
    p = await cache.get_one(Entity.PROJECTS, project_id, Project)
    if user is None or not p or user.id not in p.owner:
        raise BAD_ACCESS

    # Fetch the event to validate demo field
    event = await cache.get_one(Entity.EVENTS, project.event[0], PrivateEvent)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Validate demo field based on event's demo_links_optional setting
    validate_demo_field(project, event)

    result = db.projects.update(project_id, project.model_dump())["fields"]
    # Upsert to cache for immediate consistency
    updated = Project.model_validate({**result, "id": project_id})
    await cache.upsert_entity(Entity.PROJECTS, updated)
    return result


# Delete project
@router.delete("/{project_id}")
async def delete_project(
    project_id: Annotated[str, Path(pattern=r"^rec\w*$")],
    user: Annotated[UserInternal, Depends(get_current_user)],
):
    # Check if the user is an owner of the project or if they even exist
    p = await cache.get_one(Entity.PROJECTS, project_id, Project)
    if user is None or not p or user.id not in p.owner:
        raise BAD_ACCESS

    result = db.projects.delete(project_id)
    # Invalidate cache after deletion
    await cache.invalidate_entity(Entity.PROJECTS, project_id)
    return result


@router.get("/{project_id}")
# The regex here is to ensure that the path parameter starts with "rec" and is followed by any number of alphanumeric characters
async def get_project_endpoint(project_id: Annotated[str, Path(pattern=r"^rec\w*$")]):
    # Use cache-first lookup
    project = await cache.get_one(Entity.PROJECTS, project_id, Project)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/check/start")
async def start_project_check(project: Project) -> CheckStatus:
    """Start an asynchronous project check"""
    if not settings.review_factory_token:
        raise HTTPException(
            status_code=500, detail="Review Factory token not set on backend"
        )

    project = await cache.get_one(Entity.PROJECTS, project.id, InternalProject)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # If we have cached results, return them immediately
    if not isinstance(project.cached_auto_quality, EmptyModel):
        return CheckStatus(
            check_id="cached",
            status="completed",
            created_at=datetime.now(),
            result=project.cached_auto_quality,
        )

    # Start the check
    async with httpx.AsyncClient(timeout=30.0) as client_http:
        response = await client_http.post(
            f"{settings.review_factory_url}/start-check",
            json={
                "repo": str(project.repo),
                "image_url": str(project.image_url) if project.image_url else "",
                "demo": str(project.demo) if project.demo else "",
            },
            headers={
                "Authorization": f"Bearer {settings.review_factory_token}",
                "Content-Type": "application/json",
            },
        )
        response.raise_for_status()
        return CheckStatus.model_validate(response.json())


@router.get("/check/{check_id}")
async def poll_project_check(check_id: str) -> CheckStatus:
    """Poll the status of a project check"""
    if not settings.review_factory_token:
        raise HTTPException(
            status_code=500, detail="Review Factory token not set on backend"
        )

    # Handle cached results
    if check_id == "cached":
        raise HTTPException(
            status_code=404, detail="Cached results should be returned immediately"
        )

    # Poll the Review Factory API
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{settings.review_factory_url}/poll-check/{check_id}",
            headers={
                "Authorization": f"Bearer {settings.review_factory_token}",
                "Content-Type": "application/json",
            },
        )
        response.raise_for_status()
        return CheckStatus.model_validate(response.json())
