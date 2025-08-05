from __future__ import annotations
from podium.constants import EmptyModel, SingleRecordField, MultiRecordField, UrlField
from podium.generated.review_factory_models import Result, CheckStatus, Status
from pydantic import BaseModel, Field, StringConstraints, field_validator
from typing import Annotated, Optional
import httpx
import asyncio
import time


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
    cached_auto_quality: Result | EmptyModel = EmptyModel()

    # Allow it to be loaded as JSON
    @field_validator("cached_auto_quality", mode="before")
    @classmethod
    def load_cached_auto_quality(cls, v):
        if isinstance(v, str):
            try:
                return Result.model_validate_json(v)
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
    
    async def check_project(self, project: "Project", max_wait_time: float = 300.0, poll_interval: float = 5.0) -> Result:
        """Check a project using the Review Factory API with async polling"""
        # Start the check
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/start-check",
                json={
                    "repo": str(project.repo),
                    "image_url": str(project.image_url) if project.image_url else "",
                    "demo": str(project.demo)
                },
                headers=self.headers,
            )
            response.raise_for_status()
            check_status = CheckStatus.model_validate(response.json())
        
        check_id = check_status.check_id
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            # Poll for status
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/poll-check/{check_id}",
                    headers=self.headers,
                )
                response.raise_for_status()
                check_status = CheckStatus.model_validate(response.json())
            
            if check_status.status == Status.completed:
                if check_status.result is None:
                    raise Exception("Check completed but no result returned")
                return check_status.result
            elif check_status.status == Status.failed:
                error_msg = check_status.error or "Check failed"
                raise Exception(f"Check failed: {error_msg}")
            elif check_status.status in [Status.pending, Status.running]:
                # Wait before polling again
                await asyncio.sleep(poll_interval)
            else:
                raise Exception(f"Unknown check status: {check_status.status}")
        
        raise Exception(f"Check timed out after {max_wait_time} seconds")
