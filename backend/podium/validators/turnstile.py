"""
Cloudflare Turnstile CAPTCHA verification.

Used as a FastAPI dependency on unauthenticated endpoints (login, signup)
to replace IP-based rate limiting. Skipped when turnstile_secret_key is empty (local dev).
"""

from fastapi import HTTPException, Request
import httpx

from podium.config import settings

SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


async def require_turnstile(request: Request) -> None:
    """FastAPI dependency that verifies a Turnstile token from the X-Turnstile-Token header.
    Skips verification if no secret key is configured (local development)."""
    secret = settings.get("turnstile_secret_key", "")
    if not secret:
        return  # Dev mode — no verification

    token = request.headers.get("X-Turnstile-Token", "")
    if not token:
        raise HTTPException(status_code=403, detail="Missing Turnstile token")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                SITEVERIFY_URL,
                data={"secret": secret, "response": token},
            )
        result = response.json()
    except (httpx.RequestError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Turnstile verification unavailable") from exc

    if not result.get("success"):
        raise HTTPException(status_code=403, detail="Turnstile verification failed")
