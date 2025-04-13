from typing import Annotated
from pydantic import BaseModel, EmailStr
from podium import db
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from podium.db.user import (
    UserSignupPayload,
    UserPrivate,
    UserPublic,
    get_user_record_id_by_email,
)
from podium.routers.auth import get_current_user
from podium.constants import BAD_AUTH
from requests import HTTPError

router = APIRouter(prefix="/users", tags=["users"])

class UserExistsResponse(BaseModel):
    exists: bool


@router.get("/exists")
def user_exists(email: Annotated[EmailStr, Query(...)]) -> UserExistsResponse:
    email = email.strip().lower()
    exists = True if db.user.get_user_record_id_by_email(email) else False
    return UserExistsResponse(exists=exists)

@router.get("/{user_id}")
def get_user_public(user_id: Annotated[str, Path(title="User Airtable ID")]) -> UserPublic:
    try:
        user = db.users.get(user_id)
    except HTTPError as e:
        raise (
                HTTPException(status_code=404, detail="User not found")
                if e.response.status_code in [404, 403]
                else e
            )
            
    return UserPublic.model_validate(user["fields"])

@router.get("/current")
def get_current_user(
    current_user: Annotated[UserPrivate, Depends(get_current_user)],
) -> UserPrivate:
    if current_user:
        return current_user
    raise BAD_AUTH


# Eventually, this should probably be rate-limited
@router.post("/")
def create_user(user: UserSignupPayload):
    # Check if the user already exists
    user_id = get_user_record_id_by_email(user.email)
    if user_id:
        raise HTTPException(status_code=400, detail="User already exists")
    db.users.create(user.model_dump())


