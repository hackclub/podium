from podium.constants import SingleRecordField, MultiRecordField
from pydantic import BaseModel, Field, HttpUrl, StringConstraints
from typing import Annotated, Optional


class ProjectBase(BaseModel):
    name: Annotated[str, StringConstraints(min_length=1)]
    repo: HttpUrl
    image_url: HttpUrl
    demo: HttpUrl
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
        data["repo"] = str(self.repo)
        data["image_url"] = str(self.image_url)
        data["demo"] = str(self.demo)
        return data


class PublicProjectCreationPayload(ProjectBase): ...


class ProjectUpdate(ProjectBase): ...


class Project(ProjectBase):
    id: str
    points: int = 0
    collaborators: MultiRecordField = []
    owner: SingleRecordField


class PrivateProject(Project):
    join_code: str
