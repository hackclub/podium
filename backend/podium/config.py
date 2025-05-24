import os
from dynaconf import Dynaconf, Validator
from langchain_google_genai import ChatGoogleGenerativeAI
from quality.models import QualitySettings
from steel import Steel
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
            must_exist=True,
            # condition=lambda x: re.match(r"^SG\..+", x) is not None,
            condition=lambda x: x.startswith("SG."),
            messages={"condition": "Must start with 'SG.'"},
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
    ],
)

settings.validators.validate()

quality_settings = QualitySettings( 
    use_vision=True,
    headless=False,
    steel_client = Steel(
        steel_api_key=settings.steel_api_key,
    ),
    llm=ChatGoogleGenerativeAI(
    # https://ai.google.dev/gemini-api/docs/rate-limits
    # model="gemini-2.0-flash-exp",
    api_key=settings.gemini_api_key,
    model="gemini-2.0-flash-lite",
)
)
