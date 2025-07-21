import asyncio
from typing import Optional
from podium.constants import UrlField
from pydantic import BaseModel, ConfigDict, computed_field
from browser_use.llm.base import BaseChatModel
from steel import Steel


class Prompts(BaseModel):
    unified: str = """Evaluate if the project at ($demo) with repo at ($repo) is a valid hackathon submission.

APPROVE if:
- Demo is functional and interactive (web app, game, tool, etc.)
- Shows real functionality and provides value
- Repo exists and contains source code
- Demonstrates effort and learning

REJECT if:
- Completely broken or non-functional
- Just static pages without interactivity (unless educational)
- Videos, images, or non-interactive files
- Basic tools without advanced features
- Raw code without working demo

For deployment issues, check the repo - if it shows a legitimate project, approve."""


class QualitySettings(BaseModel):
    use_vision: bool = True
    headless: bool = False
    llm: BaseChatModel
    steel_client: Optional[Steel] = None
    prompts: Prompts = Prompts()
    session_semaphore: asyncio.Semaphore = asyncio.Semaphore(2)

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )


class ResultsResponse(BaseModel):
    valid: bool
    reason: str


class Results(BaseModel):
    demo_url: str
    repo_url: str
    image_url: str
    valid: bool
    reason: str
