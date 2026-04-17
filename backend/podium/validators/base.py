"""
Shared types for all project validators.

Each validator (itch, github, custom) returns a ValidationResult.
The background task aggregates results from all configured validators
and writes the combined status back to the Project.
"""

from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Outcome of a single validation check."""

    valid: bool
    message: str  # human-readable; shown to the user when valid=False
