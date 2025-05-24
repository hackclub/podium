import argparse
import asyncio
import os
import warnings
from langchain_google_genai import ChatGoogleGenerativeAI
from podium.db.project import Project
from quality.models import QualitySettings
import rich
from quality.quality import check_project

warnings.filterwarnings("ignore", message="unclosed transport", category=ResourceWarning)


parser = argparse.ArgumentParser(
    description="CLI for evaluating project quality. For advanced usage, import `quality` as a library. Outputs JSON."
)
parser.add_argument("--demo", required=True, help="Demo URL to evaluate.")
parser.add_argument("--repo", required=True, help="Repository URL to evaluate.")
parser.add_argument("--image", required=True, help="Image URL to evaluate.")

# Create a mutually exclusive group for settings
settings_group = parser.add_mutually_exclusive_group(required=True)
settings_group.add_argument(
    "--use-podium-settings",
    action="store_true",
    help="Use Podium's settings"
)
settings_group.add_argument(
    "--gemini-api-key",
    help="Gemini API key. The free tier should be sufficient.",
    default=os.environ.get("GEMINI_API_KEY", ""),
)
parser.add_argument(
    "--headless",
    action="store_true",
    help="Run the browser headlessly. May result in some websites blocking the agent.",
)


async def main():
    args = parser.parse_args()
    # If custom settings are not selected, ignore gemini-api-key and headless
    if args.use_podium_settings:
        from podium.config import quality_settings
        if args.headless:
            rich.print(
                "[yellow]Warning: Headless mode is not supported with Podium's settings. Ignoring --headless.[/yellow]"
            )
    else:
        quality_settings = QualitySettings(
            llm=ChatGoogleGenerativeAI(
                api_key=args.gemini_api_key,
                model="gemini-2.0-flash-lite",
            ),
            headless=args.headless,
        )

    project = Project(
        id="cli-temp",  # Temporary ID for CLI usage
        name="CLI Project",
        demo=args.demo,
        repo=args.repo,
        description="Temporary project for CLI evaluation",
        image_url=args.image,
        event=["recPLACEHOLDER"],
        owner=["recPLACEHOLDER"],
    )
    # Run the quality check
    results = await check_project(project, config=quality_settings)

    # Print the results
    rich.print_json(
        json=results.model_dump_json(),
    )
def cmd():
    os.environ["BROWSER_USE_LOGGING_LEVEL"] = "RESULT"
    asyncio.run(main())


if __name__ == "__main__":
    asyncio.run(main())