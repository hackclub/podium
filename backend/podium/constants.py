from typing import Annotated, List
from annotated_types import Len
from pydantic import StringConstraints


RECORD_REGEX = r"^rec\w*$"
# https://docs.pydantic.dev/latest/api/types/#pydantic.types.constr--__tabbed_1_2
MultiRecordField = List[Annotated[str, StringConstraints(pattern=RECORD_REGEX)]]
SingleRecordField = Annotated[
    List[Annotated[str, StringConstraints(pattern=RECORD_REGEX)]],
    Len(min_length=1, max_length=1),
]