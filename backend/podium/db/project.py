from podium.constants import SingleRecordField, MultiRecordField
from pydantic import BaseModel, Field, HttpUrl, StringConstraints, computed_field
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
    votes: MultiRecordField = []
    collaborators: MultiRecordField = []
    owner: SingleRecordField


class PrivateProject(Project):
    join_code: str

class Result(BaseModel):
    url: str
    valid: bool
    reason: str

class Results(BaseModel):
    demo: Result
    source_code: Result
    image_url: Result
    # Computed field to compile all the reasons into a single string

    @computed_field
    @property
    def reasons(self) -> str:
        individual_reasons = []
        for check in [self.demo, self.source_code, self.image_url]:
            if not check.valid and check.reason:
                individual_reasons.append(f"{check.url}: {check.reason}")
        return "\n".join(individual_reasons)
                

    @computed_field
    @property
    def valid(self) -> bool:
        return self.demo.valid and self.source_code.valid and self.image_url.valid
