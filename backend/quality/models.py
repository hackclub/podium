import asyncio
from pydantic import BaseModel, ConfigDict, computed_field
from langchain.chat_models.base import BaseChatModel
from steel import Steel


class Prompts(BaseModel):
    source_code: str = "Check if $url is a source code repository"
    demo: str = "Check if $url looks like an experienceable project, which is to say that someone at a hackathon could easily use it. If it's a web app, perfect! If it's something else, as long as it looked like it would be relatively easy to run locally, like a PyPi package or itch.io game, that's fine too. If it's a video or something like that, that's not a real project. If you can't validate it due to something like a login wall but it looks like a real project and not just 'hello world' on a page, then it's valid. Raw code is not an experiencable demo."


class QualitySettings(BaseModel):
    use_vision: bool = True
    headless: bool = False
    llm: BaseChatModel
    steel_client: Steel = None
    prompts: Prompts = Prompts()
    session_semaphore: asyncio.Semaphore = asyncio.Semaphore(2)

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )


class ResultResponse(BaseModel):
    # url: str
    valid: bool
    reason: str


class Result(ResultResponse):
    url: str


class Results(BaseModel):
    demo: Result
    source_code: Result
    image_url: Result
    # Computed field to compile all the reasons into a single string

    @computed_field
    @property
    def reasons(self) -> str:
        individual_reasons = []
        for check in [self.demo, self.source_code, self.image_url]:
            if not check.valid and check.reason:
                individual_reasons.append(f"{check.url}: {check.reason}")
        return "\n".join(individual_reasons)

    @computed_field
    @property
    def valid(self) -> bool:
        return self.demo.valid and self.source_code.valid and self.image_url.valid
