"""
Magic link authentication and JWT session management.

Flow: POST /request-login → email with magic link → GET /verify?token=... → JWT access token
The access token is a short-lived JWT (default 2 days) stored in localStorage by the frontend.
"""

from datetime import datetime, timedelta, timezone
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Query, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
import jwt
from jwt.exceptions import PyJWTError
import httpx

from podium.config import settings
from podium.constants import BAD_AUTH
from podium.validators.email import is_disposable_email
from sqlalchemy.orm import selectinload
from podium.db.postgres import User, UserPrivate, get_session, scalar_one_or_none, user_to_private, default_display_name

router = APIRouter(tags=["auth"])

SECRET_KEY = settings.jwt_secret
ALGORITHM = str(settings.jwt_algorithm)
ACCESS_TOKEN_EXPIRE_MINUTES: int = settings.jwt_expire_minutes  # type: ignore
MAGIC_LINK_EXPIRE_MINUTES = 30

HC_AUTHORIZE_URL = "https://auth.hackclub.com/oauth/authorize"
HC_TOKEN_URL = "https://auth.hackclub.com/oauth/token"
HC_ME_URL = "https://auth.hackclub.com/api/v1/me"


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
    """Send a magic link to the user's email.

    Turnstile is intentionally not required here: the signup flow sends the
    same single-use Turnstile token to both create_user and request_login, so
    validating it twice would break the second call. The rate limiter (keyed
    on user email / IP) provides bot protection instead.
    """
    email = user.email.strip().lower()
    # Block disposable emails from requesting magic links
    if is_disposable_email(email):
        raise HTTPException(status_code=400, detail="Temporary/disposable email addresses aren't allowed — please use your real email")
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

    stmt = select(User).where(User.email == email).options(selectinload(User.votes))
    user = await scalar_one_or_none(session, stmt)
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
        user=user_to_private(user),
    )


@router.get("/auth/hackclub")
async def hackclub_login(request: Request) -> RedirectResponse:
    """Initiate Hack Club OAuth login. Redirects the browser to the HC authorization page."""
    if not settings.hackclub_client_id:
        raise HTTPException(status_code=501, detail="Hack Club auth is not configured")
    state = create_access_token(
        data={"sub": "csrf"},
        expires_delta=timedelta(minutes=10),
        token_type="oauth_state",
    )
    # Derived from request so it works in all environments without an env var.
    # Normalize 127.0.0.1 → localhost so the URI matches what's registered with HC OAuth.
    redirect_uri = str(request.base_url).replace("127.0.0.1", "localhost") + "auth/hackclub/callback"
    params = urlencode({
        "client_id": settings.hackclub_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "email",
        "state": state,
    })
    return RedirectResponse(f"{HC_AUTHORIZE_URL}?{params}")


@router.get("/auth/hackclub/callback")
async def hackclub_callback(
    request: Request,
    code: Annotated[str, Query()],
    state: Annotated[str, Query()],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RedirectResponse:
    """Handle the HC OAuth callback, issue a magic-link token, and redirect to the frontend."""
    # Validate CSRF state token
    try:
        state_payload = jwt.decode(state, SECRET_KEY, algorithms=[ALGORITHM])
        if state_payload.get("token_type") != "oauth_state":
            raise HTTPException(status_code=400, detail="Invalid OAuth state")
    except PyJWTError:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    # Exchange authorization code for HC access token, then fetch user email
    try:
        async with httpx.AsyncClient() as hc:
            redirect_uri = str(request.base_url).replace("127.0.0.1", "localhost") + "auth/hackclub/callback"
            token_resp = await hc.post(HC_TOKEN_URL, data={
                "client_id": settings.hackclub_client_id,
                "client_secret": settings.hackclub_client_secret,
                "redirect_uri": redirect_uri,
                "code": code,
                "grant_type": "authorization_code",
            })
            token_resp.raise_for_status()
            hc_access_token = token_resp.json()["access_token"]

            me_resp = await hc.get(HC_ME_URL, headers={"Authorization": f"Bearer {hc_access_token}"})
            me_resp.raise_for_status()
            me = me_resp.json()
    except Exception:
        raise HTTPException(status_code=502, detail="Failed to authenticate with Hack Club")
    # HC token is discarded — only the email is kept

    identity: dict = me.get("identity", {})
    email: str = identity.get("primary_email", "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="No email returned from Hack Club")

    stmt = select(User).where(User.email == email).options(selectinload(User.votes))
    user = await scalar_one_or_none(session, stmt)
    if user is None:
        # Parse name for new users — split "First Last" if available
        full_name: str = identity.get("name", "")
        name_parts = full_name.split(" ", 1)
        first_name = name_parts[0] if name_parts else ""
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            display_name=default_display_name(first_name, last_name),
        )
        session.add(user)
        await session.commit()
        stmt = select(User).where(User.email == email).options(selectinload(User.votes))
        user = await scalar_one_or_none(session, stmt)

    # Issue a short-lived magic-link token so the existing frontend /verify flow handles the rest
    token = create_access_token(
        data={"sub": email},
        expires_delta=timedelta(minutes=15),
        token_type="magic_link",
    )
    return RedirectResponse(f"{settings.production_url}/login?token={token}")


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

    stmt = select(User).where(User.email == email).options(selectinload(User.votes))
    user = await scalar_one_or_none(session, stmt)
    if user is None:
        raise BAD_AUTH
    return user
