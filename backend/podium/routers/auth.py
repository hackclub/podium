from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
import jwt
from jwt.exceptions import PyJWTError
import httpx

from podium.config import settings
from podium.constants import BAD_AUTH
from podium.db.postgres import User, UserPrivate, get_session, scalar_one_or_none

router = APIRouter(tags=["auth"])

SECRET_KEY = settings.jwt_secret
ALGORITHM = str(settings.jwt_algorithm)
ACCESS_TOKEN_EXPIRE_MINUTES: int = settings.jwt_expire_minutes  # type: ignore
MAGIC_LINK_EXPIRE_MINUTES = 30


class UserLoginPayload(BaseModel):
    email: str


def create_access_token(
    data: dict, expires_delta: timedelta | None = None, token_type: str = "access"
) -> str:
    to_encode = data.copy()
    to_encode.update({"token_type": token_type})
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=MAGIC_LINK_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def send_magic_link(email: str, redirect: str = ""):
    token = create_access_token(
        data={"sub": email},
        expires_delta=timedelta(minutes=15),
        token_type="magic_link",
    )

    magic_link = f"{settings.production_url}/login?token={token}"
    if redirect:
        magic_link += f"&redirect={redirect}"

    if settings.loops_api_key:
        payload = {
            "email": email,
            "transactionalId": settings.loops_transactional_id,
            "dataVariables": {"auth_link": magic_link},
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://app.loops.so/api/v1/transactional",
                    headers={
                        "Authorization": f"Bearer {settings.loops_api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to send auth email")
    else:
        print("[WARNING] No Loops API key set. Not sending magic link email.")

    print(f"Magic link for {email}: {magic_link}")


@router.post("/request-login")
async def request_login(
    user: UserLoginPayload,
    redirect: Annotated[str, Query()],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Send a magic link to the user's email."""
    email = user.email.strip().lower()
    existing = await scalar_one_or_none(session, select(User).where(User.email == email))
    if existing is None:
        raise HTTPException(status_code=404, detail="User not found")
    await send_magic_link(email, redirect=redirect)


class AuthenticatedUser(BaseModel):
    access_token: str
    token_type: str
    user: UserPrivate


@router.get("/verify")
async def verify_token(
    token: Annotated[str, Query()],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AuthenticatedUser:
    """Verify a magic link token and return an access token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str | None = payload.get("sub")
        token_type: str | None = payload.get("token_type")
        if email is None or token_type != "magic_link":
            raise HTTPException(status_code=400, detail="Invalid token")
    except PyJWTError:
        raise HTTPException(status_code=400, detail="Invalid token")

    user = await scalar_one_or_none(session, select(User).where(User.email == email))
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    access_token = create_access_token(
        data={"sub": email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        token_type="access",
    )
    return AuthenticatedUser(
        access_token=access_token,
        token_type="access",
        user=UserPrivate.model_validate(user),
    )


security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    """Decode JWT and return the authenticated user."""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email: str | None = payload.get("sub")
        token_type: str | None = payload.get("token_type")
        if email is None or token_type != "access":
            raise HTTPException(status_code=400, detail="Bad JWT")
    except PyJWTError:
        raise BAD_AUTH

    user = await scalar_one_or_none(session, select(User).where(User.email == email))
    if user is None:
        raise BAD_AUTH
    return user
