from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from browser_use import Agent, Browser, BrowserConfig, Controller
import asyncio
import os
from podium import settings
from pydantic import BaseModel
import sys

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

class ProjectQuality(BaseModel):
    project_url: str
    valid: bool

controller = Controller(output_model=ProjectQuality)
browser = Browser(
            BrowserConfig(
                browser_class="firefox",
            )
        )
async def main():
    agent = Agent(
        task="Check if podium.hackclub.com looks like a proper, functional project and not something like just source code or a demo video. Don't actually try to login or signup, but do check a page or two to see if it looks like a real project that could be submitted to a hackathon or something. For example, if someone submits google.com, that's not a real project.",
        llm=llm,
        controller=controller,
        browser=browser,
    )
    result = await agent.run()
    await browser.close()
    print(result.final_result())
    print("done")

if __name__ == "__main__":
    # Error being faced even after "done" is printed
    # raise ValueError("I/O operation on closed pipe")
    # ValueError: I/O operation on closed pipe
    # https://github.com/browser-use/browser-use/issues/77 ?
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"An error occurred: {e}")
