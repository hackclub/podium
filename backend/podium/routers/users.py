from typing import Annotated
from pydantic import BaseModel, EmailStr
from podium import db, cache
from podium.cache.operations import Entity
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from podium.db.user import (
    UserSignupPayload,
    UserInternal,
    UserPublic,
    UserPrivate,
    UserUpdate,
)
from podium.routers.auth import get_current_user
from podium.constants import BAD_AUTH

router = APIRouter(prefix="/users", tags=["users"])


class UserExistsResponse(BaseModel):
    exists: bool


@router.get("/exists")
async def user_exists(email: Annotated[EmailStr, Query(...)]) -> UserExistsResponse:
    email = email.strip().lower()
    # Use cache-first lookup with Airtable fallback (no tombstone check needed - we want to know if user exists)
    exists = True if await cache.get_user_by_email(email, UserInternal) else False
    return UserExistsResponse(exists=exists)


@router.get("/current")
async def get_current_user_info(
    current_user: Annotated[UserInternal, Depends(get_current_user)],
) -> UserPrivate:
    if current_user:
        return current_user
    raise BAD_AUTH


@router.put("/current")
async def update_current_user(
    user_update: UserUpdate,
    current_user: Annotated[UserInternal, Depends(get_current_user)],
) -> UserPrivate:
    """
    Update the current user's information
    """
    if current_user is None:
        raise BAD_AUTH

    # Only include non-None values in the update
    update_data = {k: v for k, v in user_update.model_dump().items() if v is not None}

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    updated_user = db.users.update(current_user.id, update_data)

    # Cache will be invalidated by Airtable webhook
    return UserPrivate.model_validate(updated_user["fields"])


# It's important that this is under /current since otherwise /users/current will be be passed to this and `current` will be interpreted as a user_id


# The reason we're specifying response_model here is because of https://github.com/long2ice/fastapi-cache/issues/384
@router.get("/{user_id}", response_model=UserPublic)
async def get_user_public(
    user_id: Annotated[str, Path(title="User Airtable ID")],
) -> UserPublic:
    # Use cache-first lookup
    user = await cache.get_one(Entity.USERS, user_id, UserPublic)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user


# Eventually, this should probably be rate-limited
@router.post("/")
async def create_user(user: UserSignupPayload):
    # Check if the user already exists
    existing_user = await cache.get_by_formula(Entity.USERS, {"email": user.email.lower().strip()}, UserInternal)
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")
    db.users.create(user.model_dump())
