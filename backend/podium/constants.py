from fastapi import HTTPException
from pydantic import StringConstraints
from typing import Annotated
from enum import Enum


Slug = Annotated[
    str, StringConstraints(min_length=1, max_length=50, pattern=r"[-a-z0-9]+")
]

BAD_AUTH = HTTPException(status_code=401, detail="Invalid authentication credentials")
BAD_ACCESS = HTTPException(
    status_code=403, detail="You don't have permission to do this"
)


class EventPhase(str, Enum):
    """Lifecycle phases for an event, in order.

    DRAFT      - not yet visible or accepting submissions
    SUBMISSION - open for project submissions
    VOTING     - submissions closed, voting is open
    CLOSED     - voting closed, results visible
    """

    DRAFT = "draft"
    SUBMISSION = "submission"
    VOTING = "voting"
    CLOSED = "closed"


class RepoValidation(str, Enum):
    """Background validation strategy for a project's repository URL."""

    NONE = "none"      # no validation
    GITHUB = "github"  # check GitHub public API for repo existence
    CUSTOM = "custom"  # use the event's named custom validator


class DemoValidation(str, Enum):
    """Background validation strategy for a project's demo URL."""

    NONE = "none"     # no validation
    ITCH = "itch"     # check itch.io for browser-playable .game_frame
    CUSTOM = "custom" # use the event's named custom validator


class ValidationStatus(str, Enum):
    """Result of background project validation."""

    PENDING = "pending"   # not yet checked
    VALID = "valid"       # all configured validators passed
    WARNING = "warning"   # at least one validator flagged an issue
