"""
Itch.io playability validator.

Checks if an itch.io game page has a browser-playable game by looking for
the .game_frame element in the HTML.

Based on: https://github.com/devenjadhav/itch-police/blob/main/game_validator.py
"""

import re
import httpx
from bs4 import BeautifulSoup

ITCH_URL_PATTERN = re.compile(
    r"^(https?:\/\/)?[a-zA-Z0-9\-_]+\.itch\.io\/[a-zA-Z0-9\-_]+",
    re.IGNORECASE,
)


def is_itch_url(url: str) -> bool:
    """Check if URL matches itch.io game page format."""
    return bool(ITCH_URL_PATTERN.match(url))


def is_playable(url: str, timeout: float = 10.0) -> bool:
    """
    Check if an itch.io game is browser-playable.

    Args:
        url: The itch.io game page URL
        timeout: Request timeout in seconds

    Returns:
        True if the page contains a .game_frame element (browser-playable game)
    """
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")
        game_frames = soup.select(".game_frame")
        return len(game_frames) > 0
    except Exception:
        return False
