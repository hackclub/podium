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
session = steel_client.sessions.create()
print(f"View live session at: {session.session_viewer_url}")
cdp_url = f"wss://connect.steel.dev?apiKey={settings.steel_api_key}&sessionId={session.id}"
browser = Browser(config=BrowserConfig(cdp_url=cdp_url))
browser_context = BrowserContext(browser=browser)




class CheckType(Enum):
    source_code = "Check if $url is a source code repository"
    demo = "Check if $url looks like an experienceable project, which is to say that someone at a hackathon could easily use it. If it's a web app, perfect! If it's something else, as long as it looked like it would be relatively easy to run locally, like a PyPi package or itch.io game, that's fine too. If it's a video or something like that, that's not a real project. If you can't validate it due to something like a login wall but it looks like a real project and not just 'hello world' on a page, then it's valid."




@router.post("/check")
async def check_project(project: Project) -> Results:

    options = {
        "llm": llm,
        "browser_context": browser_context,
        "controller": controller,
    }

    agent = Agent(
        **options, task=Template(CheckType.demo.value).substitute(url=project.demo)
    )
    result = await agent.run(max_steps=10)
    demo_result = Result.model_validate_json(result.final_result())
    agent = Agent(
        **options,
        task=Template(CheckType.source_code.value).substitute(url=project.repo),
    )
    result = await agent.run(max_steps=10)
    source_code_result = Result.model_validate_json(result.final_result())

    await browser.close()

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
