import argparse
import asyncio
import os
import warnings
from podium.db.project import Project
import rich

warnings.filterwarnings("ignore", message="unclosed transport", category=ResourceWarning)


parser = argparse.ArgumentParser(description="CLI for quality checks.")
parser.add_argument("--demo", required=True, help="Demo URL to evaluate.")
parser.add_argument("--repo", required=True, help="Repository URL to evaluate.")
parser.add_argument("--image", required=True, help="Image URL to evaluate.")
# parser.add_argument("--steel-api-key", help="Override for Steel API key.")
# parser.add_argument("--gemini-api-key", help="Override for Gemini API key.")
async def main():
    from quality.quality import check_project
    # quality --demo "https://podium.hackclub.com" --repo "https://github.com/hackclub/podium" --image "https://assets.hackclub.com/icon-rounded.png"
    args = parser.parse_args()

    # Set the API keys if provided
    # if args.steel_api_key:
    #     settings.STEEL_API_KEY = args.steel_api_key
    # if args.gemini_api_key:
        # settings.GEMINI_API_KEY = args.gemini_api_key

    

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
    results = await check_project(project)

    # Print the results
    rich.print_json(
        json=results.model_dump_json(),
    )

def cmd():
    os.environ["BROWSER_USE_LOGGING_LEVEL"] = "RESULT"
    asyncio.run(main())


if __name__ == "__main__":
    asyncio.run(main())