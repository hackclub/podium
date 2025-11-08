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
        Validator(
            "airtable_token",
            must_exist=True,
        ),
        Validator(
            "airtable_base_id",
            must_exist=True,
        ),
        Validator(
            "airtable_events_table_id",
            must_exist=True,
        ),
        Validator(
            "airtable_users_table_id",
            must_exist=True,
        ),
        Validator(
            "airtable_referrals_table_id",
            must_exist=True,
        ),
        Validator(
            "airtable_votes_table_id",
            must_exist=True,
        ),
        Validator(
            "loops_api_key",
            # must_exist=True,
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
            "redis_url",
            # default="redis://localhost:6379",
        ),
        Validator(
            "airtable_webhook_secret",
            # must_exist=False,  # Optional - only needed if using cache invalidation webhooks
        ),
    ],
)

settings.validators.validate()
