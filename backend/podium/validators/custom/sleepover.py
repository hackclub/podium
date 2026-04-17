"""
Custom validator for Sleepover events.

Calls Review Factory to evaluate both the repo and demo URLs.
Review Factory is Hack Club's automated project quality service.

TODO: fill in REVIEW_FACTORY_URL and auth when the service is ready.
"""

import httpx

from podium.validators.base import ValidationResult

REVIEW_FACTORY_URL = ""  # e.g. "https://review-factory.hackclub.com/api/review"


async def validate_repo(repo_url: str) -> ValidationResult:
    """Ask Review Factory to review the repository."""
    if not REVIEW_FACTORY_URL:
        # Service not yet configured — pass through with a note
        return ValidationResult(valid=True, message="")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(REVIEW_FACTORY_URL, json={"url": repo_url, "type": "repo"})
            resp.raise_for_status()
            data = resp.json()
        valid = data.get("valid", False)
        message = data.get("message", "") if not valid else ""
        return ValidationResult(valid=valid, message=message)
    except Exception:
        return ValidationResult(
            valid=False,
            message="Could not reach Review Factory to validate repository.",
        )


async def validate_demo(demo_url: str) -> ValidationResult:
    """Ask Review Factory to review the demo URL."""
    if not REVIEW_FACTORY_URL:
        return ValidationResult(valid=True, message="")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(REVIEW_FACTORY_URL, json={"url": demo_url, "type": "demo"})
            resp.raise_for_status()
            data = resp.json()
        valid = data.get("valid", False)
        message = data.get("message", "") if not valid else ""
        return ValidationResult(valid=valid, message=message)
    except Exception:
        return ValidationResult(
            valid=False,
            message="Could not reach Review Factory to validate demo.",
        )
