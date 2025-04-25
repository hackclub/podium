from enum import Enum
import logging
import sys
from fastapi import APIRouter
from langchain_google_genai import ChatGoogleGenerativeAI
from browser_use import Agent, Browser, BrowserConfig, Controller
from browser_use.browser.context import BrowserContext
import asyncio
import os
from podium import settings
from podium.db.project import Project, Result, Results
from string import Template

# import atexit
import mimetypes
import httpx
from steel import Steel

logging.getLogger("browser_use").setLevel(logging.WARNING)

os.environ["GEMINI_API_KEY"] = settings.gemini_api_key
# os.environ["ANONYMIZED_TELEMETRY"] = "false" # set in .env already
os.environ["OPENAI_API_KEY"] = "..."

router = APIRouter(prefix="/projects", tags=["projects", "quality"])

controller = Controller(output_model=Result)
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-exp",
    api_key=settings.gemini_api_key,
)
# https://docs.steel.dev/overview/integrations/browser-use/quickstart
steel_client = Steel(
        steel_api_key=settings.steel_api_key,
        
)




class CheckType(Enum):
    source_code = "Check if $url is a source code repository"
    demo = "Check if $url looks like an experienceable project, which is to say that someone at a hackathon could easily use it. If it's a web app, perfect! If it's something else, as long as it looked like it would be relatively easy to run locally, like a PyPi package or itch.io game, that's fine too. If it's a video or something like that, that's not a real project. If you can't validate it due to something like a login wall but it looks like a real project and not just 'hello world' on a page, then it's valid."




@router.post("/check")
async def check_project(project: Project) -> Results:
    # Create separate sessions for each agent
    demo_session = steel_client.sessions.create()
    source_session = steel_client.sessions.create()

    print(f"View live demo session at: {demo_session.session_viewer_url}")
    print(f"View live source session at: {source_session.session_viewer_url}")

    demo_cdp_url = f"wss://connect.steel.dev?apiKey={settings.steel_api_key}&sessionId={demo_session.id}"
    source_cdp_url = f"wss://connect.steel.dev?apiKey={settings.steel_api_key}&sessionId={source_session.id}"

    demo_browser = Browser(config=BrowserConfig(cdp_url=demo_cdp_url))
    source_browser = Browser(config=BrowserConfig(cdp_url=source_cdp_url))

    demo_context = BrowserContext(browser=demo_browser)
    source_context = BrowserContext(browser=source_browser)

    options = {
        "llm": llm,
        "controller": controller,
    }

    try:
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
                task=Template(CheckType.source_code.value).substitute(url=project.repo),
                browser_context=source_context,
            ).run(max_steps=10)
        )

        # Run both agents concurrently
        demo_result_raw, source_result_raw = await asyncio.gather(demo_task, source_task)

        # Validate results with pydantic
        demo_result = Result.model_validate_json(demo_result_raw.final_result())
        source_code_result = Result.model_validate_json(source_result_raw.final_result())
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
            reason="Image url is not a raw image",
        )


# Ensure the browser is closed when the program exits
# @atexit.register
# def close_browser():
#     asyncio.run(browser.close())


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

    finally:
        ...
        # Explicitly close the browser in case of direct execution
        # await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
    # If running with vs code, this will often result, even if the program runs successfully:
    # Error in sys.excepthook:
    # Original exception was:
    # Seems to have no impact on the program


if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
