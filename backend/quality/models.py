import asyncio
from typing import Optional
from podium.constants import UrlField
from pydantic import BaseModel, ConfigDict, computed_field
from browser_use.llm.base import BaseChatModel
from steel import Steel


class Prompts(BaseModel):
    # source_code: str = "Check if $url is a source code repository"
    # demo: str = "Check if $url looks like an experienceable project, which is to say that someone at a hackathon could easily use it. If it's a web app, perfect! If it's something else, as long as it looked like it would be relatively easy to run locally, like a PyPi package or itch.io game, that's fine too. If it's a video or something like that, that's not a real project. If you can't validate it due to something like a login wall but it looks like a real project and not just 'hello world' on a page, then it's valid. Raw code is not an experiencable demo."
    unified: str = """Evaluate the demo ($demo) and repository ($repo) for a hackathon project submission.

DEMO VALIDATION CRITERIA:
- VALID: Functional web applications, interactive demos, working prototypes, portfolio sites with real content
- INVALID: YouTube videos, raw GitHub files (README.md, .mp4), broken/404 links, loading screens that never resolve, static "hello world" pages
- WAIT AND RETRY: Sites that are temporarily loading (wait 10 seconds), sites with temporary errors

REPOSITORY VALIDATION CRITERIA:
- VALID: Active GitHub repositories with source code that corresponds to the demo
- INVALID: 404 errors, empty repositories, repositories that don't match the demo content

LOGIN/SIGNUP HANDLING:
- When encountering login/signup forms, use the email: hackclubreview@inboxkitten.com
- To check for verification emails, visit: https://inboxkitten.com/inbox/hackclubreview/list
- Wait for emails to arrive and click verification links if needed
- Don't mark projects as invalid just because they require email verification

SPECIFIC RULES:
1. If demo URL contains "youtube.com", "youtu.be", or ends with ".mp4" → REJECT
2. If demo URL contains "raw.githubusercontent.com" → REJECT  
3. If demo returns 404 error → REJECT
4. If demo is just a static portfolio with real content → APPROVE
5. If demo is loading for more than 10 seconds → WAIT then retry
6. If repo returns 404 → REJECT
7. If repo doesn't contain source code related to demo → REJECT

Test the demo thoroughly. For web apps, try to interact with them. For portfolios, verify they have real content. Navigate to the repository and check if it contains relevant source code. Only approve projects that someone at a hackathon could actually experience and use."""
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
