"""
Custom validator registry.

To add a new custom validator for an event:
  1. Create a new file in this directory (e.g. my_event.py).
  2. Implement validate_repo(repo_url) and/or validate_demo(demo_url),
     each returning a ValidationResult.
  3. Register the module below under a short name.
  4. Set the event's custom_validator field to that name.

Both functions are optional — if a module only defines validate_demo,
repo validation will be skipped for that custom validator (and vice versa).
"""

from types import ModuleType
from podium.validators.custom import sleepover

# Maps custom_validator event field value → module
REGISTRY: dict[str, ModuleType] = {
    "sleepover": sleepover,
}
