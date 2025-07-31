from __future__ import annotations
from podium.constants import EmptyModel, SingleRecordField, MultiRecordField, UrlField
from podium.generated.review_factory_models import Results
from pydantic import BaseModel, Field, StringConstraints, field_validator
from typing import Annotated, Optional
import httpx


class ProjectBase(BaseModel):
    name: Annotated[str, StringConstraints(min_length=1)]
    repo: UrlField
    image_url: UrlField
    demo: UrlField
    description: Optional[str] = ""
    # event: Annotated[
    #     List[Annotated[str, StringConstraints(pattern=RECORD_REGEX)]],
    #     Len(min_length=1, max_length=1),
    # ]
    event: SingleRecordField
    hours_spent: Annotated[
        int,
        Field(
            description="A lower-bound estimate of the number of hours spent on the project. Only used for general statistics.",
            ge=0,
        ),
    ] = 0

    def model_dump(self, *args, **kwargs):
        data = super().model_dump(*args, **kwargs)
        # If they are HttpUrl, they need to be converted to str
        # data["repo"] = str(self.repo)
        # data["image_url"] = str(self.image_url)
        # data["demo"] = str(self.demo)
        return data


class PublicProjectCreationPayload(ProjectBase): ...


class ProjectUpdate(ProjectBase): ...


class Project(ProjectBase):
    id: str
    points: int = 0
    votes: MultiRecordField = []
    collaborators: MultiRecordField = []
    owner: SingleRecordField


class PrivateProject(Project):
    join_code: str


class InternalProject(PrivateProject):
    cached_auto_quality: Results | EmptyModel = EmptyModel()

    # Allow it to be loaded as JSON
    @field_validator("cached_auto_quality", mode="before")
    @classmethod
    def load_cached_auto_quality(cls, v):
        if isinstance(v, str):
            try:
                return Results.model_validate_json(v)
            except Exception:
                return EmptyModel()
        return v


class ReviewFactoryClient:
    """Simple HTTP client for Review Factory API"""
    
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
    
    async def check_project(self, project: "Project") -> Results:
        """Check a project using the Review Factory API"""
        async with httpx.AsyncClient(timeout=300.0) as client:  # 5 minute timeout
            response = await client.post(
                f"{self.base_url}/check",
                json=project.model_dump(),
                headers=self.headers,
            )
            response.raise_for_status()
            return Results.model_validate(response.json())
