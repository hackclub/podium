from pathlib import Path
from typing import Annotated, Optional, Self, cast
from pydantic import BaseModel, ConfigDict, Field, model_validator
from browser_use.llm.base import BaseChatModel
from browser_use.llm import ChatGroq
from decouple import Config, RepositoryEnv
from collections import ChainMap
from loguru import logger
from steel import Steel

APP_PORT = "5173"

# Only load environment files if they exist
env_files_to_load = [".env"]
env_files: list[RepositoryEnv] = []
for env_file in env_files_to_load:
    if Path(env_file).exists():
        with open(env_file, "r") as f:
            line_count = len(f.readlines())
            logger.info(f"Loading {env_file} ({line_count} lines)")
            env_files.append(RepositoryEnv(env_file))

config = Config(ChainMap(*env_files)) if env_files else Config(ChainMap())  # type: ignore


class AiTestSettings(BaseModel):
    use_vision: bool = config("USE_VISION", default=True, cast=bool)
    headless: bool = config("HEADLESS", default=False, cast=bool)
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )
    llm: Annotated[Optional[BaseChatModel], Field(default=None)]
    steel_client: Optional[Steel] = Field(default=None, exclude=True)
    ngrok_auth_token: str = config("NGROK_AUTHTOKEN")

    @model_validator(mode="after")
    def configure_llm(self) -> Self:
        """Configure LLM and Steel client based on environment configuration"""
        # Configure LLM if not already set
        if self.llm is None:
            llm_model = cast(str, config("LLM_MODEL", default="groq")).lower()
            if llm_model == "groq":
                model = "meta-llama/llama-4-maverick-17b-128e-instruct"
                groq_api_key = cast(Optional[str], config("GROQ_API_KEY", default=None))
                if not groq_api_key:
                    raise ValueError("GROQ_API_KEY is required when LLM_MODEL=groq")
                self.llm = ChatGroq(model=model, api_key=groq_api_key)
        if self.steel_client is None:
            steel_api_key = cast(str, config("STEEL_API_KEY"))
            if steel_api_key:
                self.steel_client = Steel(steel_api_key=steel_api_key)

        return self


settings = AiTestSettings()
