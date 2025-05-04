from pydantic import BaseModel, computed_field


class ResultResponse(BaseModel):
    # url: str
    valid: bool
    reason: str
class Result(ResultResponse):
    url: str

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