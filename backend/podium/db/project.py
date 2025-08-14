from __future__ import annotations
from podium.constants import EmptyModel, SingleRecordField, MultiRecordField, UrlField
from podium.generated.review_factory_models import Unified
from pydantic import BaseModel, Field, StringConstraints, field_validator
from typing import Annotated, Optional


class ProjectBase(BaseModel):
    name: Annotated[str, StringConstraints(min_length=1)]
    repo: UrlField
    image_url: UrlField
    demo: UrlField
    description: Optional[str] = ""
    # event: Annotated[
    #     List[Annotated[str, StringC0onstraints(pattern=RECORD_REGEX)]],
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
    cached_auto_quality: Unified | EmptyModel = EmptyModel()

    # Allow it to be loaded as JSON
    @field_validator("cached_auto_quality", mode="before")
    @classmethod
    def load_cached_auto_quality(cls, v):
        if isinstance(v, str):
            try:
                return Unified.model_validate_json(v)
            except Exception:
                return EmptyModel()
        return v


