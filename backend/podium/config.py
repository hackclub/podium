import os
from dynaconf import Dynaconf, Validator
from browser_use.llm import ChatGoogle
from steel import Steel

# type: ignore

environment = os.getenv("PYTHON_ENV", "development")
print(f"Using environment: {environment}")

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
            "sendgrid_api_key",
            # must_exist=True,
            # condition=lambda x: re.match(r"^SG\..+", x) is not None,
            # condition=lambda x: x.startswith("SG."),
            # messages={"condition": "Must start with 'SG.'"},
        ),
        # Validator(
        # "sendgrid_from_email",
        # must_exist=False,
        # default="",
        # ),
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
    ],
)

settings.validators.validate()
