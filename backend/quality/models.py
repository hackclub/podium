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
- Show genuine effort and learning, not just a template or basic example
- Have at least one advanced feature or substantial functionality

EXAMPLE VALID PROJECT TYPES (APPROVE these):
- Interactive web applications with multiple features and good UX (e.g., full-stack apps, complex tools)
- Playable games (web-based, downloadable, or on platforms like itch.io) with clear mechanics and gameplay
- Useful packages/libraries with comprehensive documentation and real use cases
- Desktop applications with working installers or clear installation instructions
- Mobile apps with clear installation instructions and demonstrated functionality
- Browser extensions with live demos or very clear installation instructions
- Data visualization tools with interactive features and real data
- Educational tools and learning platforms with substantial content and functionality
- Productivity tools and utilities with clear value proposition and advanced features
- Creative tools (image editors, music makers, etc.) with functional features beyond basic templates
- Visual/creative projects (optical illusions, animations, interactive art) with clear visual impact and interactivity
- Social platforms and communication tools with working features and user interaction
- Personal portfolios with substantial interactive content or exceptional design and functionality
- CRUD applications with additional features, good UX, or innovative approach beyond basic forms
- Interactive demonstrations and showcases with educational or entertainment value
- Scientific simulations and visualizations with clear functionality and educational value
- Blogs and content sites with substantial, well-designed, and organized content with clear value
- Static sites with meaningful, well-organized information and clear value beyond basic pages
- Projects with minor technical issues but clear core functionality and substantial features
- Projects that demonstrate learning and effort, even if simple but well-executed with clear value

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
- Any login-required app with no public demo or clear functionality demonstration
- Any simple meme generator, basic form, or trivial web app without substantial features
- Any executable download without a working demo or clear installation instructions
- Any project that appears to be a template or basic example without customization
- Any project with broken core functionality or major technical issues
- Any basic text input/output tool without substantial processing or features
- Any simple image viewer, text display, or basic display tool without advanced functionality
- Any project that only demonstrates basic HTML/CSS/JS without meaningful interactivity
- Any tool that just wraps existing APIs without adding substantial value or features

REPOSITORY VALIDATION:
The repository must:
- Actually exist and be accessible
- Contain the source code for the demo project
- Be the repository homepage, not a specific file or subdirectory
- Have clear documentation or evidence it's the right repository

TESTING GUIDELINES:
- For web apps: Confirm at least one advanced feature is present and functional (not just basic forms)
- For games: Must be playable with clear game mechanics and actual gameplay
- For packages: Must have comprehensive documentation and real use cases
- For extensions: Must have a live demo or very clear installation instructions
- For visual/creative projects: Must demonstrate clear interactive or visual functionality with impact
- For static sites: Must have substantial, well-organized content with clear value beyond basic info
- For projects with minor issues: If core functionality works, approve despite minor bugs
- For login-required apps: REJECT unless there's a clear public demo or the app is clearly legitimate and functional
- If you encounter network errors, retry up to 3 times before marking as invalid
- Test actual functionality, not just appearance
- Be fair but maintain quality standards - don't approve projects that are clearly basic or non-functional
- Look for substantial features, not just basic functionality

SPECIAL CASES:
- Optical illusions and visual effects: APPROVE if they demonstrate clear visual functionality and impact
- Blogs and content sites: APPROVE if they have substantial, well-organized content with clear value
- Login-required apps: REJECT unless there's a clear public demo or the app is clearly legitimate
- Projects with minor bugs: APPROVE if core functionality is working and the project shows effort
- Static informational sites: APPROVE if content is substantial, well-organized, and provides clear value
- Simple tools: REJECT unless they have additional features, good UX, or demonstrate clear learning
- Basic form tools: REJECT unless they have substantial processing, validation, or advanced features
- Meme generators: REJECT unless they have advanced features like AI, multiple templates, or substantial customization
- Deployment issues: If a project has a 404 or deployment error but the repo shows it's a legitimate project, REJECT the demo but note the deployment issue
- Broken functionality: If core functionality is broken (like search not working), REJECT even if other parts work
- Basic games: Simple games like Pong, Snake, etc. should be REJECTED unless they have advanced features, good graphics, or innovative gameplay

IMPORTANT: Maintain quality standards while being fair. Only approve projects that demonstrate genuine functionality, effort, and value. Reject projects that are clearly basic, non-functional, or lack substantial content. Err on the side of rejection for projects that don't meet the quality bar, but be fair to projects that show genuine effort and functionality. Look for projects that go beyond basic examples and demonstrate real learning and development. Be especially strict about rejecting projects with broken core functionality or deployment issues."""
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
