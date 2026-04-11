"""
Email validation utilities.

Uses MailChecker (55k+ disposable domain blocklist) to detect
throwaway email addresses at signup and login.
"""

import logging

import MailChecker

logger = logging.getLogger(__name__)


def is_disposable_email(email: str) -> bool:
    """Return True if the email is from a known disposable/temporary email provider.
    Returns False on any error (fail open) to avoid blocking legitimate signups."""
    try:
        return not MailChecker.is_valid(email)
    except Exception as exc:
        logger.warning("MailChecker failed for %s: %s — treating as non-disposable", email, exc)
        return False
