# from __future__ import annotations
import asyncio
from rich import print as pprint
# import logging
from browser_use import BrowserProfile, Controller
from browser_use import BrowserSession, Agent

# from browser_use.llm import ChatOpenAI
from string import Template
import mimetypes
import httpx
from podium import config 
from quality.models import QualitySettings, ResultsResponse, Results
from pydantic import ValidationError
from podium.db.project import Project

# os.environ["OPENAI_API_KEY"] = "..."
# os.environ["ANONYMIZED_TELEMETRY"] = "false" # set in .env, along with BROWSER_USE_LOGGING_LEVEL=result
# logging.basicConfig(level=logging.DEBUG)

controller = Controller(output_model=ResultsResponse)


async def check_project(project: "Project", config: QualitySettings) -> Results:
    # Acquire the semaphore to ensure no more than 2 concurrent sessions
    async with config.session_semaphore:
        if config.steel_client:
            # Create separate sessions for each agent
            browser_session = config.steel_client.sessions.create()
            print(f"View live session at: {browser_session.session_viewer_url}")

            browser_cdp_url = f"wss://connect.steel.dev?apiKey={config.steel_client.steel_api_key}&sessionId={browser_session.id}"

            browser = BrowserSession(cdp_url=browser_cdp_url)
        else:
            browser = BrowserSession(
                browser_profile=BrowserProfile(
                    headless=config.headless,
                ),
            )



        options = {
            "llm": config.llm,
            "controller": controller,
            "max_failures": 2,
            "use_vision": config.use_vision,
        }

        try:
            # Run the browser agent for demo and source_code only
            agent_task = asyncio.create_task(
                Agent(
                    **options,
                    task=Template(config.prompts.unified).substitute(
                        repo=project.repo,
                        demo=project.demo,
                    ),
                    browser_session=browser,
                ).run(
                    max_steps=15 # default is 100
                )
            )

            results_raw = await asyncio.gather(agent_task)
            agent_result = results_raw[0]
            final_json = agent_result.final_result()
            pprint(final_json)
            if final_json is not None:
                # Parse the agent result
                result = ResultsResponse.model_validate_json(final_json)
            else:
                result = ResultsResponse(
                    valid=False,
                    reason="Agent did not return a result"
                )

        except ValidationError as e:
            print(f"Validation error occurred: {e}")
            result = ResultsResponse(
                valid=False,
                reason="Validation error occurred"
            )
        finally:
            # Close browser
            if browser:
                await browser.close()
            # Release session if used
            if config.steel_client and 'browser_session' in locals():
                config.steel_client.sessions.release(browser_session.id)

        # Check image validation
        image_valid = await is_raw_image(project.image_url)
        
        return Results(
            demo_url=project.demo,
            repo_url=project.repo,
            image_url=project.image_url,
            valid=result.valid,
            reason=result.reason,
            image_valid=image_valid
        )


async def is_raw_image(url: str) -> bool:
    """
    Check if the given URL points to a raw image file.
    This is done by checking the file extension or the Content-Type header.
    """
    # Check file extension
    mime_type, _ = mimetypes.guess_type(url)
    if mime_type and mime_type.startswith("image/"):
        return True

    # Check Content-Type header
    try:
        async with httpx.AsyncClient() as client:
            response = await client.head(url, timeout=5)
            content_type = response.headers.get("Content-Type", "")
            return content_type.startswith("image/")
    except Exception as e:
        print(f"Error checking image URL: {e}")
        return False


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
        ),
#     QualitySettings(
#     use_vision=True,
#     headless=False,
#     steel_client=None
#     llm=ChatGoogle(
#         # https://ai.google.dev/gemini-api/docs/rate-limits
#         # model="gemini-2.0-flash-exp",   
#         api_key=os.environ["GEMINI_API_KEY"],
#         model="gemini-2.0-flash-lite",
#     ),
# )
        config=config.quality_settings,
    ) 
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

    # If running with vs code, this will often result, even if the program runs successfully:
