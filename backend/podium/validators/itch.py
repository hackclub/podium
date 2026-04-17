"""
Itch.io project validator.

Instant check: regex match on the URL shape (used frontend-side too).
Background check: fetches the page and looks for a .game_frame element,
which is only present for browser-playable games.

Based on: https://github.com/devenjadhav/itch-police
"""

import re
import httpx
from bs4 import BeautifulSoup

from podium.validators.base import ValidationResult

ITCH_URL_PATTERN = re.compile(
    r"^https?://[a-zA-Z0-9\-_]+\.itch\.io/[a-zA-Z0-9\-_]+",
    re.IGNORECASE,
)


def is_itch_url(url: str) -> bool:
    """Return True if the URL matches the itch.io game page format."""
    return bool(ITCH_URL_PATTERN.match(url))


async def validate(demo_url: str, timeout: float = 10.0) -> ValidationResult:
    """
    Check whether an itch.io game is browser-playable.

    Fetches the game page and looks for a .game_frame element. Games without
    'Run in browser' enabled on itch.io will not have this element.
    """
    if not is_itch_url(demo_url):
        return ValidationResult(
            valid=False,
            message="Demo URL must be an itch.io game page (e.g. username.itch.io/game-name).",
        )

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(demo_url)
            response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")
        if soup.select(".game_frame"):
            return ValidationResult(valid=True, message="")
        return ValidationResult(
            valid=False,
            message='Game is not browser-playable. Enable "Run game in browser" in your itch.io project settings.',
        )
    except Exception:
        return ValidationResult(
            valid=False,
            message="Could not reach the itch.io page to verify playability.",
        )
