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
    scalar_one_or_none,
)
from podium.routers.auth import get_current_user

router = APIRouter(prefix="/users", tags=["users"])


class UserExistsResponse(BaseModel):
    exists: bool


@router.get("/exists")
async def user_exists(
    email: Annotated[EmailStr, Query(...)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserExistsResponse:
    email_lower = email.strip().lower()
    user = await scalar_one_or_none(session, select(User).where(User.email == email_lower))
    return UserExistsResponse(exists=user is not None)


@router.get("/current")
async def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserPrivate:
    return UserPrivate.model_validate(current_user)


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

    current_user.sqlmodel_update(update_data)

    await session.commit()
    await session.refresh(current_user)
    return UserPrivate.model_validate(current_user)


@router.get("/{user_id}", response_model=UserPublic)
async def get_user_public(
    user_id: Annotated[UUID, Path(title="User ID")],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserPublic:
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserPublic.model_validate(user)


@router.post("/")
async def create_user(
    user: UserSignup,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    email = user.email.strip().lower()
    existing = await scalar_one_or_none(session, select(User).where(User.email == email))
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    # Convert None values to empty strings for optional fields
    user_data = user.model_dump()
    for field in ["last_name", "display_name", "phone", "street_1", "street_2", "city", "state", "zip_code", "country"]:
        if user_data.get(field) is None:
            user_data[field] = ""
    user_data["email"] = email

    new_user = User.model_validate(user_data)
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    return {"id": str(new_user.id)}
