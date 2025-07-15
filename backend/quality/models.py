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
For the demo, it has to be a real, experiencable project. That means it should be easy to run and use. Here's examples of what's valid:
    - A web app
    - A PyPi package
    - An itch.io game
    - An NPM package
    - A website with real content, no placeholder or lorem ipsum content
    Here's examples of what's not valid:
    - A video
    - A login-protected app
    - A raw code repository
    - A placeholder page
    - A 404 page

Do some basic checks on the demo to ensure you can click around and what not. If it's a game, and you can tell it probably functions, don't attempt to play it.
If you encounter a login wall, don't reject the submission just because of that, try to test the public features.

The repository should contain the source code for the demo. If it does, it's valid. If the repository does not exist or is empty, it's not valid.

Before completing your evaluation, make sure both the demo and repository have been completely reviewed.
"""
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
