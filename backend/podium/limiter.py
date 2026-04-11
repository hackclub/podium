"""
Rate limiting configuration.

Uses user-based rate limiting (email from JWT) for authenticated endpoints.
Unauthenticated endpoints use Cloudflare Turnstile instead (see validators/turnstile.py).
"""

from starlette.requests import Request
from slowapi import Limiter
import jwt as pyjwt

from podium.config import settings


def get_user_email(request: Request) -> str:
    """Extract user email from JWT for rate limiting authenticated endpoints.
    Falls back to the client IP if no valid token is present, so unauthenticated
    requests don't all share one rate-limit bucket."""
    from slowapi.util import get_remote_address

    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        try:
            payload = pyjwt.decode(
                auth[7:], settings.jwt_secret, algorithms=[str(settings.jwt_algorithm)]
            )
            if email := payload.get("sub"):
                return email
        except Exception:
            pass
    return get_remote_address(request)


def get_user_or_ip_for_sentry(request: Request) -> str:
    """Extract user email or IP for Sentry user context. Not used for rate limiting."""
    from slowapi.util import get_remote_address
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        try:
            payload = pyjwt.decode(
                auth[7:], settings.jwt_secret, algorithms=[str(settings.jwt_algorithm)]
            )
            if email := payload.get("sub"):
                return email
        except Exception:
            pass
    return get_remote_address(request)


# Rate limiter keyed by user email (for authenticated endpoints only)
limiter = Limiter(key_func=get_user_email)
