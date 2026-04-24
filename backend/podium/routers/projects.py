from secrets import token_urlsafe
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Path, Query, Request
from sqlalchemy import func
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
    get_ro_session,
    scalar_one_or_none,
)
from podium.db.postgres.base import async_session_factory
from podium.db.postgres.user import has_ysws_pii
from podium.routers.auth import get_current_user
from podium.limiter import limiter
from podium.validators import itch, github, CUSTOM_VALIDATORS
from podium.validators.base import ValidationResult
from podium.constants import BAD_AUTH, BAD_ACCESS, RepoValidation, DemoValidation, ValidationStatus

router = APIRouter(prefix="/projects", tags=["projects"])


def validate_demo_field(demo: str | None, event: Event) -> None:
    """Raise 422 if demo is required but missing."""
    if not event.demo_links_optional and not (demo and demo.strip()):
        raise HTTPException(status_code=422, detail="Demo URL is required for this event")


async def _run_background_validation(project_id: UUID) -> None:
    """Open a fresh DB session and run all validators for the project's event config.

    Updates project.validation_status and project.validation_message in-place.
    Runs after the response is sent so it never blocks the user.
    """
    if not async_session_factory:
        return

    async with async_session_factory() as session:
        project = await scalar_one_or_none(
            session,
            select(Project).where(Project.id == project_id).options(selectinload(Project.votes)),
        )
        if not project:
            return

        event = await session.get(Event, project.event_id)
        if not event:
            return

        messages: list[str] = []
        all_valid = True

        try:
            # ── repo validation ──────────────────────────────────────────────────
            if event.repo_validation == RepoValidation.GITHUB and project.repo:
                result = await github.validate(project.repo)
                if not result.valid:
                    all_valid = False
                    if result.message:
                        messages.append(result.message)
            elif event.repo_validation == RepoValidation.CUSTOM and event.custom_validator:
                module = CUSTOM_VALIDATORS.get(event.custom_validator)
                if module and hasattr(module, "validate_repo"):
                    result = await module.validate_repo(project.repo)
                    if not result.valid:
                        all_valid = False
                        if result.message:
                            messages.append(result.message)

            # ── demo validation ──────────────────────────────────────────────────
            if event.demo_validation == DemoValidation.ITCH and project.demo:
                result = await itch.validate(project.demo)
                if not result.valid:
                    all_valid = False
                    if result.message:
                        messages.append(result.message)
            elif event.demo_validation == DemoValidation.CUSTOM and event.custom_validator:
                module = CUSTOM_VALIDATORS.get(event.custom_validator)
                if module and hasattr(module, "validate_demo"):
                    result = await module.validate_demo(project.demo)
                    if not result.valid:
                        all_valid = False
                        if result.message:
                            messages.append(result.message)
        except Exception as e:
            all_valid = False
            messages.append(f"Validation error: {e}")
        finally:
            project.validation_status = ValidationStatus.VALID if all_valid else ValidationStatus.WARNING
            project.validation_message = " | ".join(messages)
            await session.commit()


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
            selectinload(User.owned_projects).options(
                selectinload(Project.votes),
                selectinload(Project.owner),
                selectinload(Project.collaborators),
            ),
            selectinload(User.projects_collaborating).options(
                selectinload(Project.votes),
                selectinload(Project.owner),
                selectinload(Project.collaborators),
            ),
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
    background_tasks: BackgroundTasks,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Create a new project and schedule background validation."""
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

    if event.require_ysws_pii and not has_ysws_pii(user):
        raise HTTPException(status_code=400, detail="This event requires your address and date of birth on your profile before you can submit a project")

    while True:
        join_code = token_urlsafe(3).upper()
        code_exists = await scalar_one_or_none(
            session, select(Project).where(func.upper(Project.join_code) == join_code)
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

    background_tasks.add_task(_run_background_validation, new_project.id)
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
        .where(func.upper(Project.join_code) == join_code.upper())
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
    background_tasks: BackgroundTasks,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Update a project and re-schedule background validation."""
    project = await scalar_one_or_none(
        session,
        select(Project)
        .where(Project.id == project_id)
        .options(
            selectinload(Project.votes),
            selectinload(Project.owner),
            selectinload(Project.collaborators),
        ),
    )
    if not project or project.owner_id != user.id:
        raise BAD_ACCESS

    event = await session.get(Event, project.event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    validate_demo_field(project_update.demo, event)

    update_data = project_update.model_dump(exclude_unset=True, exclude_none=True)
    project.sqlmodel_update(update_data)
    # Reset to pending so the UI reflects that re-validation is in progress
    project.validation_status = ValidationStatus.PENDING
    project.validation_message = ""

    await session.commit()
    await session.refresh(project)

    background_tasks.add_task(_run_background_validation, project.id)
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
    session: Annotated[AsyncSession, Depends(get_ro_session)],
) -> ProjectPublic:
    """Get a project by ID."""
    project = await scalar_one_or_none(
        session,
        select(Project)
        .where(Project.id == project_id)
        .options(
            selectinload(Project.votes),
            selectinload(Project.owner),
            selectinload(Project.collaborators),
        ),
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectPublic.model_validate(project)


@router.post("/validate")
@limiter.limit("10/minute")
async def validate_project(
    request: Request,
    project_id: Annotated[UUID, Query(description="Project ID to validate")],
    background_tasks: BackgroundTasks,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> ValidationResult:
    """Trigger re-validation for a project and return the current (pre-run) status.

    The actual validation runs asynchronously after this response. Poll
    GET /projects/{id} to see the updated validation_status once done.
    """
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != user.id:
        raise BAD_ACCESS

    project.validation_status = ValidationStatus.PENDING
    project.validation_message = ""
    await session.commit()

    background_tasks.add_task(_run_background_validation, project.id)
    return ValidationResult(valid=True, message="Validation queued")
