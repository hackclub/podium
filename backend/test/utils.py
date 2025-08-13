import logging
from typing import Mapping, Any
from loguru import logger

def magic_url(temp_user_tokens: Mapping[str, Any]) -> str:
    """Return a preformatted instruction containing the Steel magic login link."""
    logger.info(f"Magic login link: {temp_user_tokens['magic_link_url']}")
    return f"Use this magic login link to sign in: {temp_user_tokens['magic_link_url']}."


