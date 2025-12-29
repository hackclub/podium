"""
Application configuration using Dynaconf.

All settings are loaded from environment variables with PODIUM_ prefix,
or from settings.toml/.secrets.toml files. Dynaconf strips the prefix,
so PODIUM_DATABASE_URL becomes settings.database_url.
"""

import os
from dynaconf import Dynaconf, Validator

# type: ignore

print(f"Using environment: {os.getenv('ENV_FOR_DYNACONF', '')}")
settings = Dynaconf(
    envvar_prefix="PODIUM",
    load_dotenv=True,
    settings_files=["settings.toml", ".secrets.toml"],
    merge_enabled=True,
    environments=True,
)
settings.validators.register(
    validators=[
        # Airtable settings - optional, only needed for scripts/migrate_from_airtable.py
        # Can be removed after production cutover is complete
        Validator(
            "airtable_token",
            default="",
        ),
        Validator(
            "airtable_base_id",
            default="",
        ),
        Validator(
            "airtable_events_table_id",
            default="",
        ),
        Validator(
            "airtable_users_table_id",
            default="",
        ),
        Validator(
            "airtable_referrals_table_id",
            default="",
        ),
        Validator(
            "airtable_votes_table_id",
            default="",
        ),
        Validator(
            "loops_api_key",
            default="",
        ),
        Validator(
            "loops_transactional_id",
            must_exist=True,
        ),
        Validator(
            "jwt_secret",
            must_exist=True,
        ),
        Validator(
            "jwt_algorithm",
            default="HS256",
        ),
        Validator(
            "jwt_expire_minutes",
            # 2 days. People can always log in again
            default=2880,
        ),
        Validator(
            "review_factory_url",
            default="https://review-factory-backend.hackclub.com",
        ),
        Validator(
            "review_factory_token",
            default="",
        ),
        Validator(
            "database_url",
            must_exist=True,
        ),
        Validator(
            "production_url",
            default="http://localhost:5173",
        ),
    ],
)

settings.validators.validate()
