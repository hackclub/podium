from starlette.requests import Request
from slowapi import Limiter
from slowapi.util import get_remote_address
import jwt as pyjwt

from podium.config import settings

limiter = Limiter(key_func=get_remote_address)


def get_user_or_ip(request: Request) -> str:
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
