from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, EmailStr
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from podium.db.postgres import (
    User,
    UserPublic,
    UserPrivate,
    UserSignup,
    UserUpdate,
    get_session,
    get_ro_session,
    scalar_one_or_none,
    user_to_private,
    default_display_name,
)
from podium.routers.auth import get_current_user
from podium.validators.email import is_disposable_email
from podium.validators.turnstile import require_turnstile

router = APIRouter(prefix="/users", tags=["users"])


class UserExistsResponse(BaseModel):
    exists: bool


@router.get("/exists")
async def user_exists(
    email: Annotated[EmailStr, Query(...)],
    session: Annotated[AsyncSession, Depends(get_ro_session)],
    _turnstile: None = Depends(require_turnstile),
) -> UserExistsResponse:
    email_lower = email.strip().lower()
    user = await scalar_one_or_none(session, select(User).where(User.email == email_lower))
    return UserExistsResponse(exists=user is not None)


@router.get("/current")
async def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserPrivate:
    return user_to_private(current_user)


@router.put("/current")
async def update_current_user(
    user_update: UserUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserPrivate:
    """Update the current user's information."""
    update_data = user_update.model_dump(exclude_unset=True, exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    # If display_name is being cleared, fall back to "First L."
    if "display_name" in update_data and not update_data["display_name"].strip():
        first = update_data.get("first_name", current_user.first_name)
        last = update_data.get("last_name", current_user.last_name)
        update_data["display_name"] = default_display_name(first, last)

    current_user.sqlmodel_update(update_data)

    await session.commit()
    await session.refresh(current_user)
    return user_to_private(current_user)


@router.get("/{user_id}", response_model=UserPublic)
async def get_user_public(
    user_id: Annotated[UUID, Path(title="User ID")],
    session: Annotated[AsyncSession, Depends(get_ro_session)],
) -> UserPublic:
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserPublic.model_validate(user)


@router.post("/")
async def create_user(
    user: UserSignup,
    session: Annotated[AsyncSession, Depends(get_session)],
    _turnstile: None = Depends(require_turnstile),
):
    email = user.email.strip().lower()
    if is_disposable_email(email):
        raise HTTPException(status_code=400, detail="Temporary/disposable email addresses aren't allowed — please use your real email")
    existing = await scalar_one_or_none(session, select(User).where(User.email == email))
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    # exclude_none lets the User model's field defaults ("") apply for unprovided optional fields
    user_data = user.model_dump(exclude_none=True)
    user_data["email"] = email
    # Default display_name to "First L." if not explicitly provided
    if not user_data.get("display_name", "").strip():
        user_data["display_name"] = default_display_name(user_data["first_name"], user_data.get("last_name", ""))

    new_user = User.model_validate(user_data)
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    return {"id": str(new_user.id)}
