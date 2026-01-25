from secrets import token_urlsafe
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload

from podium.db.postgres import (
    User,
    Event,
    Project,
    ProjectPublic,
    ProjectPrivate,
    ProjectCreate,
    ProjectUpdate,
    get_session,
    scalar_one_or_none,
)
from podium.routers.auth import get_current_user
from podium.validators import is_itch_url, is_playable
from podium.constants import BAD_AUTH, BAD_ACCESS


class ValidationResult(BaseModel):
    valid: bool
    message: str

router = APIRouter(prefix="/projects", tags=["projects"])


def validate_demo_field(demo: str | None, event: Event) -> None:
    """Validate demo field based on event settings."""
    if not event.demo_links_optional and not (demo and demo.strip()):
        raise HTTPException(status_code=422, detail="Demo URL is required for this event")


@router.get("/mine")
async def get_projects(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[ProjectPrivate]:
    """Get projects owned by or collaborated on by the current user."""
    stmt = (
        select(User)
        .where(User.id == user.id)
        .options(
            selectinload(User.owned_projects).selectinload(Project.votes),
            selectinload(User.projects_collaborating).selectinload(Project.votes),
        )
    )
    u = await scalar_one_or_none(session, stmt)
    if not u:
        raise BAD_AUTH
    all_projects = list(u.owned_projects) + list(u.projects_collaborating)
    return [ProjectPrivate.model_validate(p) for p in all_projects]


@router.post("/")
async def create_project(
    project: ProjectCreate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Create a new project."""
    stmt = (
        select(Event)
        .where(Event.id == project.event_id)
        .options(selectinload(Event.attendees))
    )
    event = await scalar_one_or_none(session, stmt)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    validate_demo_field(project.demo, event)

    if user not in event.attendees:
        raise HTTPException(status_code=403, detail="Owner not part of event")

    while True:
        join_code = token_urlsafe(3).upper()
        code_exists = await scalar_one_or_none(
            session, select(Project).where(Project.join_code == join_code)
        )
        if not code_exists:
            break

    new_project = Project.model_validate(
        project,
        update={
            "demo": project.demo or "",
            "description": project.description or "",
            "join_code": join_code,
            "owner_id": user.id,
        },
    )
    session.add(new_project)
    await session.commit()
    await session.refresh(new_project)
    return {"id": str(new_project.id), "join_code": new_project.join_code}


@router.post("/join")
async def join_project(
    join_code: Annotated[str, Query(description="Project join code")],
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Join a project as a collaborator."""
    stmt = (
        select(Project)
        .where(Project.join_code == join_code.upper())
        .options(selectinload(Project.collaborators))
    )
    project = await scalar_one_or_none(session, stmt)
    if not project:
        raise HTTPException(status_code=404, detail="No project found")

    if user.id == project.owner_id or user in project.collaborators:
        raise HTTPException(status_code=400, detail="User is already a collaborator or owner")

    stmt = (
        select(Event)
        .where(Event.id == project.event_id)
        .options(selectinload(Event.attendees))
    )
    event = await scalar_one_or_none(session, stmt)
    if not event or user not in event.attendees:
        raise BAD_ACCESS

    project.collaborators.append(user)
    await session.commit()
    return {"message": "Successfully joined project"}


@router.put("/{project_id}")
async def update_project(
    project_id: Annotated[UUID, Path(title="Project ID")],
    project_update: ProjectUpdate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Update a project."""
    project = await scalar_one_or_none(
        session,
        select(Project)
        .where(Project.id == project_id)
        .options(selectinload(Project.votes)),
    )
    if not project or project.owner_id != user.id:
        raise BAD_ACCESS

    event = await session.get(Event, project.event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    validate_demo_field(project_update.demo, event)

    update_data = project_update.model_dump(exclude_unset=True, exclude_none=True)
    project.sqlmodel_update(update_data)

    await session.commit()
    await session.refresh(project)
    return ProjectPublic.model_validate(project)


@router.delete("/{project_id}")
async def delete_project(
    project_id: Annotated[UUID, Path(title="Project ID")],
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Delete a project."""
    project = await session.get(Project, project_id)
    if not project or project.owner_id != user.id:
        raise BAD_ACCESS

    await session.delete(project)
    await session.commit()
    return {"message": "Project deleted"}


@router.get("/{project_id}")
async def get_project_endpoint(
    project_id: Annotated[UUID, Path(title="Project ID")],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProjectPublic:
    """Get a project by ID."""
    project = await scalar_one_or_none(
        session,
        select(Project)
        .where(Project.id == project_id)
        .options(selectinload(Project.votes)),
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectPublic.model_validate(project)


@router.post("/validate")
async def validate_project(
    project_id: Annotated[UUID, Query(description="Project ID to validate")],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ValidationResult:
    """Validate a project's demo URL for itch.io browser playability."""
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not project.demo:
        return ValidationResult(valid=False, message="No demo URL provided")

    if not is_itch_url(project.demo):
        return ValidationResult(valid=False, message="Demo URL must be an itch.io game page")

    if is_playable(project.demo):
        return ValidationResult(valid=True, message="Game is browser-playable")
    else:
        return ValidationResult(
            valid=False,
            message="Game is not browser-playable. Enable 'Run game in browser' in your itch.io project settings.",
        )
