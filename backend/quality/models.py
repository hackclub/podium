import asyncio
from typing import Optional
from podium.constants import UrlField
from pydantic import BaseModel, ConfigDict, computed_field
from browser_use.llm.base import BaseChatModel
from steel import Steel


class Prompts(BaseModel):
    # source_code: str = "Check if $url is a source code repository"
    # demo: str = "Check if $url looks like an experienceable project, which is to say that someone at a hackathon could easily use it. If it's a web app, perfect! If it's something else, as long as it looked like it would be relatively easy to run locally, like a PyPi package or itch.io game, that's fine too. If it's a video or something like that, that's not a real project. If you can't validate it due to something like a login wall but it looks like a real project and not just 'hello world' on a page, then it's valid. Raw code is not an experiencable demo."
    unified: str = """Evaluate hackathon project demo ($demo) and repository ($repo).

## VALIDATION CRITERIA

### ✅ ACCEPTED PROJECT TYPES:
- Web applications (React, Vue, Svelte, etc.)
- Interactive demos and prototypes
- Working software with real functionality
- Portfolios with substantial content
- PyPi/npm packages
- Itch.io games and interactive experiences
- Mobile apps with web demos

### ❌ REJECTION CRITERIA:
- YouTube videos or video content
- Raw GitHub files (README.md, .py files, etc.)
- 404 errors or broken links
- Static "hello world" pages
- Empty or placeholder content
- URLs containing: "youtube.com", "youtu.be", ".mp4", "raw.githubusercontent.com"

### 🔍 EVALUATION PROCESS:
1. **Demo Check**: Verify the demo is functional and interactive
    - If you're unable to interact with the demo due to issues with calling browser APIs, but it looks functional, mark as valid.
2. **Repository Check**: Confirm source code exists and relates to the demo
3. **Content Check**: Ensure substantial, non-placeholder content
4. **Accessibility**: For login-protected apps, test public features only

### 📋 REQUIREMENTS:
- Demo must be experienceable (someone can use it at a hackathon)
- Repository must contain relevant source code
- Project must demonstrate real functionality
- No placeholder or template content

Provide clear reasoning for your decision. Ensure you have checked both the demo and repository."""
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
