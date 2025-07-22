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
- Projects with minor technical issues but clear effort and learning
- Static sites that demonstrate coding skills and creativityf

REJECT if:
- Completely broken or non-functional
- Just videos, images, or non-interactive files without code
- Basic tools without any advanced features or learning
- Raw code without any working demo or documentation
- Projects that show no effort or learning

Be more lenient with:
- Portfolio sites (approve if they show multiple projects and effort)
- Projects with minor deployment issues but good code
- Projects with partial functionality but clear learning
- Static sites that demonstrate web development skills

For deployment issues, check the repo - if it shows a legitimate project with effort, approve. If the demo is deemed non-functional, check if the source code is legit and shows effort to determine if the project should be rejected, as in some cases, the demo is functional unbenownstly."""


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
