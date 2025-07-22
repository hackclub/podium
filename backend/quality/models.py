import asyncio
from typing import Optional

from browser_use.llm.base import BaseChatModel
from pydantic import BaseModel, ConfigDict
from steel import Steel


class Prompts(BaseModel):
    unified: str = """Evaluate if the project at ($demo) with source code at ($repo) is a valid hackathon submission.

APPROVE if:
- Demo is functional and interactive (web app, game, tool, etc.)
- Shows real functionality and provides value
- Repo exists and contains source code
- Demonstrates effort and learning
- Projects with minor technical issues but clear effort and learning
- Static sites that demonstrate coding skills and creativity
- Packages on PyPi, NPM, Crates, etc.

REJECT if:
- Completely broken or non-functional
- The demo is a video
    - Only exception is if the project is a physical hardware project, such as a robot 
- Basic tools without any advanced features or learning
- Raw code without any working demo or documentation
- GitHub release without files that are clearly one-click executable binaries (e.g. .exe, .dmg, .sh not .zip, .tar, .gz, etc.)

Be more lenient with:
- Portfolio sites (approve if they show multiple projects and effort)
- Projects with partial functionality but clear learning
- Static sites that demonstrate web development skills

If the demo is deemed non-functional (a button doesn't work, for example) but still loads, check if the source code is legit and shows effort to determine if the project should be rejected, as in some cases, the demo is functional but it's a issue with the browser. The demo should still load at least, though."""


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
    image_valid: bool
