import asyncio
from typing import Optional
from podium.constants import UrlField
from pydantic import BaseModel, ConfigDict, computed_field
from browser_use.llm.base import BaseChatModel
from steel import Steel


class Prompts(BaseModel):
    # source_code: str = "Check if $url is a source code repository"
    # demo: str = "Check if $url looks like an experienceable project, which is to say that someone at a hackathon could easily use it. If it's a web app, perfect! If it's something else, as long as it looked like it would be relatively easy to run locally, like a PyPi package or itch.io game, that's fine too. If it's a video or something like that, that's not a real project. If you can't validate it due to something like a login wall but it looks like a real project and not just 'hello world' on a page, then it's valid. Raw code is not an experiencable demo."
    unified: str = """Evaluate a project with the demo at ($demo) and repository at ($repo).

DEMO VALIDATION:
The demo must be a real, experiencable project that demonstrates functionality and value. To be VALID, the demo must:
- Be functional and interactive (web app, game, tool, etc.)
- Demonstrate clear functionality that provides value
- Be accessible and usable
- Show genuine effort and learning

APPROVE projects that:
- Have working functionality and provide clear value
- Are interactive and demonstrate real features
- Show effort and learning, even if simple
- Are functional web applications, games, tools, or utilities
- Have educational or entertainment value
- Demonstrate real problem-solving or creativity
- Are complete and working, even if basic

REJECT projects that:
- Are completely broken or non-functional
- Are just static pages with no interactivity
- Are placeholder/template sites with no real content
- Are videos, images, or non-interactive files
- Have 404 errors or fail to load
- Are just raw code repositories without demos
- Are clearly incomplete or abandoned

REPOSITORY VALIDATION:
The repository must:
- Exist and be accessible
- Contain source code for the project
- Be the repository homepage
- Have some documentation or evidence it's the right repo

TESTING GUIDELINES:
- Test if the project actually works and provides value
- Look for real functionality, not just appearance
- Be practical - if it works and has value, approve it
- Don't be overly strict about "advanced features"
- Focus on whether someone would find it useful
- If it's functional and demonstrates learning, approve it
- Only reject if it's clearly broken or non-functional

IMPORTANT: Be practical and fair. If a project works, provides value, and shows effort, approve it. Only reject projects that are clearly broken, non-functional, or lack any real value. Err on the side of approval for functional projects."""
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



class Result(BaseModel):
    valid: bool
    reason: str
    tested_url: str


class ResultsResponse(BaseModel):
    demo: Result
    source_code: Result
    # Computed field to compile all the reasons into a single string


class Results(ResultsResponse):
    image_url: Result
    @computed_field
    @property
    def reasons(self) -> str:
        individual_reasons = []
        for name, check in zip(["demo", "source_code", "image_url"], [self.demo, self.source_code, self.image_url]):
            if not check.valid and check.reason:
                individual_reasons.append(f"{name}: {check.reason}")
        return "\n".join(individual_reasons)

    @computed_field
    @property
    def valid(self) -> bool:
        return self.demo.valid and self.source_code.valid and self.image_url.valid
