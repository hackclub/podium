# from __future__ import annotations
from enum import Enum
# import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from browser_use import Agent, Browser, BrowserConfig, Controller
from browser_use.browser.context import BrowserContext
import asyncio
import os
# from langchain_openai import ChatOpenAI
from podium import settings
from string import Template
import mimetypes
import httpx
from podium.db.quality import Result, ResultResponse ,Results
from pydantic import BaseModel, ValidationError, computed_field
from steel import Steel
from podium.db.project import Project

USE_STEEL = False

os.environ["GEMINI_API_KEY"] = settings.gemini_api_key
os.environ["OPENAI_API_KEY"] = "..."
# os.environ["ANONYMIZED_TELEMETRY"] = "false" # set in .env, along with BROWSER_USE_LOGGING_LEVEL=result
# logging.basicConfig(level=logging.DEBUG)


# https://ai.google.dev/gemini-api/docs/rate-limits
# model="gemini-2.0-flash-exp",
use_vision = True
model="gemini-2.0-flash-lite"
llm = ChatGoogleGenerativeAI(
    api_key=settings.gemini_api_key,
    model=model,
)
# llm=ChatOpenAI(base_url='https://ai.hackclub.com/', model='abcxyz', api_key='abcxyz', verbose=True)

controller = Controller(output_model=ResultResponse)

if USE_STEEL:
    # https://docs.steel.dev/overview/integrations/browser-use/quickstart
    steel_client = Steel(
        steel_api_key=settings.steel_api_key,
    )

# Create a global semaphore to limit concurrent Steel sessions
steel_session_semaphore = asyncio.Semaphore(2)
# TODO: https://fastapi.tiangolo.com/tutorial/background-tasks/

class CheckType(Enum):
    source_code = "Check if $url is a source code repository"
    demo = "Check if $url looks like an experienceable project, which is to say that someone at a hackathon could easily use it. If it's a web app, perfect! If it's something else, as long as it looked like it would be relatively easy to run locally, like a PyPi package or itch.io game, that's fine too. If it's a video or something like that, that's not a real project. If you can't validate it due to something like a login wall but it looks like a real project and not just 'hello world' on a page, then it's valid."


async def check_project(project: "Project") -> Results:
    # Acquire the semaphore to ensure no more than 2 concurrent sessions
    async with steel_session_semaphore:
        if USE_STEEL:
            # Create separate sessions for each agent
            demo_session = steel_client.sessions.create()
            source_session = steel_client.sessions.create()
            print(f"View live demo session at: {demo_session.session_viewer_url}")
            print(f"View live source session at: {source_session.session_viewer_url}")

            demo_cdp_url = f"wss://connect.steel.dev?apiKey={settings.steel_api_key}&sessionId={demo_session.id}"
            source_cdp_url = f"wss://connect.steel.dev?apiKey={settings.steel_api_key}&sessionId={source_session.id}"

            demo_browser = Browser(config=BrowserConfig(cdp_url=demo_cdp_url))
            source_browser = Browser(config=BrowserConfig(cdp_url=source_cdp_url))
        else:
            browser = Browser()
            demo_browser = browser
            source_browser = browser

        demo_context = BrowserContext(browser=demo_browser)
        source_context = BrowserContext(browser=source_browser)

        options = {
            "llm": llm,
            "controller": controller,
            "max_failures": 2,
            "use_vision": use_vision,
        }

        try:
            # Initialize variables with default invalid results
            demo_result = Result(
                url=str(project.demo),
                valid=False,
                reason="Demo URL validation failed unexpectedly",
            )
            source_code_result = Result(
                url=str(project.repo),
                valid=False,
                reason="Source code URL validation failed unexpectedly",
            )

            # Create tasks for concurrent execution
            demo_task = asyncio.create_task(
                Agent(
                    **options,
                    task=Template(CheckType.demo.value).substitute(url=project.demo),
                    browser_context=demo_context,
                ).run(max_steps=10)
            )

            source_task = asyncio.create_task(
                Agent(
                    **options,
                    task=Template(CheckType.source_code.value).substitute(
                        url=project.repo
                    ),
                    browser_context=source_context,
                ).run(max_steps=10)
            )

            # Run both agents concurrently
            demo_result_raw, source_result_raw = await asyncio.gather(
                demo_task, source_task
            )

            # Validate results with pydantic
            demo_result = ResultResponse.model_validate_json(demo_result_raw.final_result())
            source_code_result = ResultResponse.model_validate_json(
                source_result_raw.final_result()
            )
            # Add the URL to the results
            demo_result = Result(
                **demo_result.model_dump(),
                url=str(project.demo)
            )   
            source_code_result = Result(
                **source_code_result.model_dump(),
                url=str(project.repo)
            )
        except ValidationError:
            # Default values are already set in case the URL is inaccessible or something else goes with the agent
            pass
        finally:
            # Close browser contexts
            if demo_context:
                await demo_context.close()
            if source_context:
                await source_context.close()

            # Close browsers
            if demo_browser:
                await demo_browser.close()
            if source_browser:
                await source_browser.close()

            # Release sessions
            if USE_STEEL:
                if demo_session:
                    steel_client.sessions.release(demo_session.id)
                if source_session:
                    steel_client.sessions.release(source_session.id)

        return Results(
            demo=demo_result,
            source_code=source_code_result,
            image_url=await is_raw_image(str(project.image_url)),
        )


async def is_raw_image(url: str) -> Result:
    """
    Check if the given URL points to a raw image file.
    This is done by checking the file extension or the Content-Type header.
    """
    # Check file extension
    mime_type, _ = mimetypes.guess_type(url)
    if (mime_type and mime_type.startswith("image/")):
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
            is_image_type = content_type.startswith("image/")
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
            reason="Image URL is not a raw image",
        )


async def main():
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
    # {
    #     "id": "123",
    #     "name": "Podium",
    #     "demo": "https://podium.hackclub.com",
    #     "repo": "https://github.com/hackclub/podium",
    #     "description": "A platform for hackathons",
    #     "image_url": "https://assets.hackclub.com/icon-rounded.png",
    #     "event": ["recj2PpwaPPxGsAbk"],
    #     "owner": ["recj2PpwaPPxGsAbk"]
    # }
    print(f"{test_run}\n\n{test_run.valid}\n{test_run.reasons}")


if __name__ == "__main__":
    asyncio.run(main())
    # If running with vs code, this will often result, even if the program runs successfully:
    # Error in sys.excepthook:
    # Original exception was:
    # Seems to have no impact on the program



