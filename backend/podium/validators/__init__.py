"""
Project validators.

Public surface: import individual validator modules for their validate()
functions, or use base.ValidationResult as the return type.

    from podium.validators import itch, github
    from podium.validators.base import ValidationResult
    from podium.validators import CUSTOM_VALIDATORS
"""

from podium.validators.base import ValidationResult
from podium.validators import itch, github
from podium.validators.custom import REGISTRY as CUSTOM_VALIDATORS

__all__ = [
    "ValidationResult",
    "itch",
    "github",
    "CUSTOM_VALIDATORS",
]
