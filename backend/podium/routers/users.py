from typing import Annotated
from pydantic import BaseModel, EmailStr
from podium import db
from fastapi import APIRouter, Depends, HTTPException, Query
from podium.db.user import (
    UserSignupPayload,
    User,
    get_user_record_id_by_email,
)
from podium.routers.auth import get_current_user
from podium.constants import BAD_AUTH

router = APIRouter(prefix="/users", tags=["users"])


# DISABLE THIS IN PRODUCTION
# @router.get("/")
# def get_users():
#     return db.users.all()


@router.get("/current")
def get_current_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
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


class UserExistsResponse(BaseModel):
    exists: bool


@router.get("/exists")
def user_exists(email: Annotated[EmailStr, Query(...)]) -> UserExistsResponse:
    email = email.strip().lower()
    exists = True if db.user.get_user_record_id_by_email(email) else False
    return UserExistsResponse(exists=exists)
