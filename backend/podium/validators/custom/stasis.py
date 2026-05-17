"""
Custom validator for Stasis events.

Calls Review Factory to evaluate both the repo and demo URLs.
Review Factory is Hack Club's automated project quality service.

TODO: fill in REVIEW_FACTORY_URL and auth when the service is ready.
"""

import httpx

from podium.validators.base import ValidationResult

REVIEW_FACTORY_URL = ""  # e.g. "https://review-factory.hackclub.com/api/review"


async def _validate_url(url: str, url_type: str) -> ValidationResult:
    if not REVIEW_FACTORY_URL:
        return ValidationResult(valid=True, message="")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(REVIEW_FACTORY_URL, json={"url": url, "type": url_type})
            resp.raise_for_status()
            data = resp.json()
        valid = data.get("valid", False)
        message = data.get("message", "") if not valid else ""
        return ValidationResult(valid=valid, message=message)
    except Exception:
        return ValidationResult(
            valid=False,
            message=f"Could not reach Review Factory to validate {url_type}.",
        )


async def validate_repo(repo_url: str) -> ValidationResult:
    return await _validate_url(repo_url, "repo")


async def validate_demo(demo_url: str) -> ValidationResult:
    return await _validate_url(demo_url, "demo")
