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
    demo = "Check if $url looks like a experienceable website, game, or submission for a hackathon. If someone submits a video, that's not a real project. If someone submits a source code repository, that's not a real project. If someone submits an itch.io project that looks like a proper game, that's a real project. If someone submits something that people will be able to easily experience, that's a real project. If someone submits a web app or website that isn't just a simple \"hello world\" page and not something existing like google.com, that's a real project. If there's a login wall on the web app that the user submitted, just check if the website looks real and not just a demo video or source code. Don't try to signup."

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

    # Computed field to compile all the reasons into a single string
    @computed_field
    @property
    def reasons(self) -> str:
        if self.demo.valid and self.source_code.valid:
            return ""
        return "\n".join([
            f"Demo: {self.demo.reason}",
            f"Source Code: {self.source_code.reason}"
        ])


async def check_project(project: Project) -> Results:
    agent = Agent(
            llm=llm,
            controller=controller,
        browser=browser
        )
    
    agent.task = Template(CheckType.demo.value).substitute(url=project.url)
    result = await agent.run(max_steps=10)
    demo_result = result.final_result()

    agent.task = Template(CheckType.source_code.value).substitute(url=project.repo)
    result = await agent.run(max_steps=10)
    source_code_result = result.final_result()

    return Results(
        demo=demo_result,
        source_code=source_code_result,
    )
        


async def main():
    try:
        agent = Agent(
            task=Template(CheckType.demo.value).substitute(url="https://podium.hackclub.com"),
            llm=llm,
            controller=controller,
            browser=browser
        )
        result = await agent.run(max_steps=10)
        print(result.final_result())
    finally:
        # Ensure the browser is closed even if an exception occurs
        await browser.close()
        print("Browser closed")
    print("done")

if __name__ == "__main__":
    asyncio.run(main())
    # If running with vs code, this will often result, even if the program runs successfully:
    # Error in sys.excepthook:
    # Original exception was:
    # Seems to have no impact on the program
