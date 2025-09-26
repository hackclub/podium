from typing import Annotated
from pydantic import BaseModel, EmailStr
from podium import db
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi_cache.decorator import cache
from fastapi_cache import FastAPICache
from podium.db.user import (
    UserSignupPayload,
    UserInternal,
    UserPublic,
    UserPrivate,
    UserUpdate,
    UserBase,
    get_user_by_email,
)
from podium.routers.auth import get_current_user
from podium.constants import AIRTABLE_NOT_FOUND_CODES, BAD_AUTH
from requests import HTTPError

router = APIRouter(prefix="/users", tags=["users"])





class UserExistsResponse(BaseModel):
    exists: bool


@router.get("/exists")
def user_exists(email: Annotated[EmailStr, Query(...)]) -> UserExistsResponse:
    email = email.strip().lower()
    exists = True if db.user.get_user_by_email(email, UserBase) else False
    return UserExistsResponse(exists=exists)


@router.get("/current")
def get_current_user_info(
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
    
    # Clear the cache for this user's public profile
    await FastAPICache.clear(namespace="users")
    
    return UserPrivate.model_validate(updated_user["fields"])


# It's important that this is under /current since otherwise /users/current will be be passed to this and `current` will be interpreted as a user_id

# The reason we're specifying response_model here is because of https://github.com/long2ice/fastapi-cache/issues/384
@router.get("/{user_id}", response_model=UserPublic)
# @cache(expire=15*60, namespace="users")
async def get_user_public(
    user_id: Annotated[str, Path(title="User Airtable ID")],
) -> UserPublic:
    try:
        user = db.user.get_users_from_record_ids([user_id], UserPublic)
    except HTTPError as e:
        raise (
            HTTPException(status_code=404, detail="User not found")
            if e.response.status_code in AIRTABLE_NOT_FOUND_CODES
            else e
        )
    
    return user


# Eventually, this should probably be rate-limited
@router.post("/")
def create_user(user: UserSignupPayload):
    # Check if the user already exists
    existing_user = get_user_by_email(user.email, UserBase)
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")
    db.users.create(user.model_dump())
