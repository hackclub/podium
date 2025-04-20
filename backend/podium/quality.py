from enum import Enum
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from browser_use import Agent, Browser, BrowserConfig, Controller
import asyncio
import os
from podium import settings
from podium.db.project import Project
from pydantic import BaseModel, computed_field
from string import Template
import atexit
import mimetypes
import httpx


os.environ["GEMINI_API_KEY"] = settings.gemini_api_key
os.environ["ANONYMIZED_TELEMETRY"] = "false"
os.environ["OPENAI_API_KEY"] = "..."

# llm = ChatOpenAI(
#     base_url="https://ai.hackclub.com", # ai.hackclub.com doesn't seem to work yet
# )

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-exp",
    api_key=settings.gemini_api_key,
)

# llm=ChatOllama(model="phi4-mini")


class Result(BaseModel):
    url: str
    valid: bool
    reason: str


class CheckType(Enum):
    source_code = "Check if $url is a source code repository"
    demo = "Check if $url looks like a experienceable website, game, or submission for a hackathon. If someone submits a video, that's not a real project. If someone submits a source code repository, that's not a real project. If someone submits an itch.io project that looks like a proper game, that's a real project. If someone submits something that people will be able to easily experience, that's a real project. If someone submits a web app or website that isn't just a simple \"hello world\" page and not something existing like google.com, that's a real project. If there's a login wall on the web app that the user submitted, just check if the website looks real and not just a demo video or source code. Don't try to signup. Please note, unless the page at $url looks like something like itch.io, steam, or PyPi, treat it as a web app."


controller = Controller(output_model=Result)
browser = Browser(
    BrowserConfig(
        # browser_class="firefox",
    )
)


# task="Check if podium.hackclub.com looks like a proper, functional project and not something like just source code or a demo video. Don't actually try to login or signup, but do check a page or two to see if it looks like a real project that could be submitted to a hackathon or something. For example, if someone submits google.com, that's not a real project. If you can't validate it due to something like a login wall but it looks like a real project and not just 'hello world' on a page, then it's valid.",


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


async def check_project(project: Project) -> Results:
    options = {
        "llm": llm,
        "browser": browser,
        "controller": controller,
    }

    agent = Agent(**options, task=Template(CheckType.demo.value).substitute(url=project.demo))
    result = await agent.run(max_steps=10)
    demo_result = Result.model_validate_json(
        result.final_result()
    )
    agent = Agent(
        **options,
        task=Template(CheckType.source_code.value).substitute(url=project.repo),
    )
    result = await agent.run(max_steps=10)
    source_code_result = Result.model_validate_json(
        result.final_result()
    )

    # Check if the image URL is a raw image


    return Results(
        demo=demo_result,
        source_code=source_code_result,
        image_url=await is_raw_image(str(project.image_url))
    )

async def is_raw_image(url: str) -> Result:
    """
    Check if the given URL points to a raw image file.
    This is done by checking the file extension or the Content-Type header.
    """
    # Check file extension
    mime_type, _ = mimetypes.guess_type(url)
    if mime_type and mime_type.startswith("image/"):
        return Result(
            url=url,
            valid=True,
            reason="",
        )

    # Check Content-Type header
    try:
        async with httpx.AsyncClient() as client:
            response = await client.head(url, timeout=5)
            content_type = response.headers.get("Content-Type", "")
            is_image_type =  content_type.startswith("image/")
            return Result(
                url=url,
                valid=is_image_type,
                reason="",
            )
    except Exception as e:
        print(f"Error checking image URL: {e}")
        return Result(
            url=url,
            valid=False,
            reason="Image url is not a raw image",
        )


# Ensure the browser is closed when the program exits
@atexit.register
def close_browser():
    asyncio.run(browser.close())


async def main():
    try:
        test_run = await check_project(
                Project(
                    id="123",
                    name="Podium",
                    demo="https://podium.hackclub.com",
                    repo="https://github.com/hackclub/podium",
                    description="A platform for hackathons",
                    image_url="https://assets.hackclub.com/icon-rounded.png",
                    event=["recj2PpwaPPxGsAbk"],
                    owner=["recj2PpwaPPxGsAbk"],
                )
            )
        print(f"{test_run}\n\n{test_run.valid}\n{test_run.reasons}")
    finally:
        # Explicitly close the browser in case of direct execution
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
    # If running with vs code, this will often result, even if the program runs successfully:
    # Error in sys.excepthook:
    # Original exception was:
    # Seems to have no impact on the program
