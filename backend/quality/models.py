import asyncio
from typing import Optional
from podium.constants import UrlField
from pydantic import BaseModel, ConfigDict, computed_field
from browser_use.llm.base import BaseChatModel
from steel import Steel


class Prompts(BaseModel):
    # source_code: str = "Check if $url is a source code repository"
    # demo: str = "Check if $url looks like an experienceable project, which is to say that someone at a hackathon could easily use it. If it's a web app, perfect! If it's something else, as long as it looked like it would be relatively easy to run locally, like a PyPi package or itch.io game, that's fine too. If it's a video or something like that, that's not a real project. If you can't validate it due to something like a login wall but it looks like a real project and not just 'hello world' on a page, then it's valid. Raw code is not an experiencable demo."
    unified: str = """Evaluate a project with the demo at ($demo) and repository at ($repo).

DEMO VALIDATION:
The demo must be a real, experiencable project that demonstrates SUBSTANTIAL and MEANINGFUL functionality. To be VALID, the demo must meet ALL of the following:
- Be a fully functional, interactive web application, package, or game
- Demonstrate clear, useful functionality that goes beyond basic examples
- Be accessible and usable by someone at a hackathon

EXAMPLE VALID PROJECT TYPES (APPROVE these):
- Interactive web applications with multiple features
- Playable games (web-based, downloadable, or on platforms like itch.io)
- Useful packages/libraries with clear documentation and examples
- Desktop applications with working installers or executables
- Mobile apps with clear installation instructions
- Browser extensions with live demos
- Data visualization tools
- Educational tools and learning platforms
- Productivity tools and utilities
- Creative tools (image editors, music makers, etc.)
- Visual/creative projects (optical illusions, animations, interactive art)
- Social platforms and communication tools
- Personal portfolios with substantial interactive content
- Basic CRUD applications with additional features or good UX
- Interactive demonstrations and showcases
- Scientific simulations and visualizations
- Blogs and content sites with substantial, well-designed content
- Static sites with meaningful, well-organized information
- Projects with minor technical issues but clear functionality
- Projects that demonstrate learning and effort, even if simple
- Login-required apps that clearly show functionality (approve if the app looks legitimate)

EXPLICITLY REJECT the following (NOT VALID):
- Any video, screenshot, image file, or non-interactive file
- Any raw code repository without a live demo
- Any placeholder, "coming soon", or basic static site with no functionality
- Any 404 page, broken link, or site that fails to load after 3 retries
- Any simple static website with only navigation and no interactive features
- Any Replit project that doesn't actually run or demonstrate core functionality
- Any simple calculator, todo list, or basic CRUD app without additional features or good UX
- Any website that just displays information without interactive functionality
- Any project where the demo and repo do not clearly match

REPOSITORY VALIDATION:
The repository must:
- Actually exist and be accessible
- Contain the source code for the demo project
- Be the repository homepage, not a specific file or subdirectory
- Have clear documentation or evidence it's the right repository

TESTING GUIDELINES:
- For web apps: Confirm at least one advanced feature is present and functional
- For games: Must be playable with clear game mechanics
- For packages: Must have comprehensive documentation and real use cases
- For extensions: Must have a live demo or very clear installation instructions
- For visual/creative projects: Must demonstrate clear interactive or visual functionality
- For static sites: Must have substantial, well-organized content
- For projects with minor issues: If core functionality works, approve despite minor bugs
- For login-required apps: If the app looks legitimate and functional, approve it
- If you encounter network errors, retry up to 3 times before marking as invalid
- Test actual functionality, not just appearance
- Be lenient with projects that show genuine effort and learning

SPECIAL CASES:
- Optical illusions and visual effects: APPROVE if they demonstrate clear visual functionality
- Blogs and content sites: APPROVE if they have substantial, well-organized content
- Login-required apps: APPROVE if they clearly show legitimate functionality
- Projects with minor bugs: APPROVE if core functionality is working
- Static informational sites: APPROVE if content is substantial and well-organized

IMPORTANT: Be reasonable and fair in your evaluation. If a project demonstrates clear value and functionality, approve it. Only reject projects that are clearly broken, non-functional, or lack substantial content. Err on the side of approval for projects that show genuine effort and functionality. Remember that hackathon projects are learning experiences and may have minor issues."""
class QualitySettings(BaseModel):
    use_vision: bool = True
    headless: bool = False
    llm: BaseChatModel
    steel_client: Optional[Steel] = None
    prompts: Prompts = Prompts()
    session_semaphore: asyncio.Semaphore = asyncio.Semaphore(2)

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )



class Result(BaseModel):
    valid: bool
    reason: str
    tested_url: str


class ResultsResponse(BaseModel):
    demo: Result
    source_code: Result
    # Computed field to compile all the reasons into a single string


class Results(ResultsResponse):
    image_url: Result
    @computed_field
    @property
    def reasons(self) -> str:
        individual_reasons = []
        for name, check in zip(["demo", "source_code", "image_url"], [self.demo, self.source_code, self.image_url]):
            if not check.valid and check.reason:
                individual_reasons.append(f"{name}: {check.reason}")
        return "\n".join(individual_reasons)

    @computed_field
    @property
    def valid(self) -> bool:
        return self.demo.valid and self.source_code.valid and self.image_url.valid
