import argparse
import asyncio
import os
import warnings
from podium.db.project import Project
import rich
from quality.quality import check_project

warnings.filterwarnings("ignore", message="unclosed transport", category=ResourceWarning)


parser = argparse.ArgumentParser(description="CLI for quality checks.")
parser.add_argument("--demo", required=True, help="Demo URL to evaluate.")
parser.add_argument("--repo", required=True, help="Repository URL to evaluate.")
parser.add_argument("--image", required=True, help="Image URL to evaluate.")
parser.add_argument(
    "--use-podium-settings",
    action="store_true",
    help="Use Podium's settings"
)
    

# parser.add_argument("--steel-api-key")
# parser.add_argument("--gemini-api-key")
async def main():
    # quality --demo "https://podium.hackclub.com" --repo "https://github.com/hackclub/podium" --image "https://assets.hackclub.com/icon-rounded.png" --use-podium-settings
    args = parser.parse_args()

    if args.use_podium_settings:
        from podium.config import quality_settings
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
    else:   
        print("At the moment, you must use settings from Podium or import `quality` as a library and use it like that.")

def cmd():
    os.environ["BROWSER_USE_LOGGING_LEVEL"] = "RESULT"
    asyncio.run(main())


if __name__ == "__main__":
    asyncio.run(main())