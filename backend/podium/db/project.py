from __future__ import annotations
from podium.constants import EmptyModel, SingleRecordField, MultiRecordField, UrlField
from podium.generated.review_factory_models import Unified
from pydantic import BaseModel, Field, StringConstraints, field_validator
from typing import Annotated, Optional, List, Type, TypeVar
from pyairtable.formulas import OR, EQ, Field as AirtableField
from podium.db import tables


class ProjectBase(BaseModel):
    name: Annotated[str, StringConstraints(min_length=1)]
    repo: UrlField
    image_url: UrlField
    demo: UrlField
    description: Optional[str] = ""
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


class ProjectCreationPayload(ProjectBase): ...


class ProjectUpdate(ProjectBase): ...
    
class Project(ProjectBase):
    id: str
    points: int = 0
    votes: MultiRecordField = []
    collaborators: MultiRecordField = []
    owner: SingleRecordField

    """In addition to the normal fields, we also have lookup fields in Airtable so we can use formulas:
    - event_id
    - owner_id
    """


class PrivateProject(Project):
    """This is for project owners and project collaborators"""
    join_code: str


class AdminProject(PrivateProject):
    """Event admins should see the AdminProject version of each project associated with an event"""
    cached_auto_quality: Unified | EmptyModel = EmptyModel()

    @field_validator("cached_auto_quality", mode="before")
    @classmethod
    def load_cached_auto_quality(cls, v):
        """This way, cached_auto_quality can be loaded as JSON so in Airtable, we can just have a single field for cached quality status"""
        if isinstance(v, str):
            try:
                return Unified.model_validate_json(v)
            except Exception:
                return EmptyModel()
        return v



class InternalProject(AdminProject):
    """This should never exit the backend"""
    ...


T = TypeVar("T", bound=ProjectBase)
def get_projects_from_record_ids(record_ids: List[str], model: Type[T]) -> List[T]:
    projects_table = tables["projects"]
    if not record_ids:
        return []
    
    # Use PyAirtable's OR and EQ functions for multiple record ID matching
    expressions = [EQ(AirtableField("id"), record_id) for record_id in record_ids]
    formula = OR(*expressions)
    
    records = projects_table.all(formula=formula)
    return [model.model_validate(record["fields"]) for record in records]