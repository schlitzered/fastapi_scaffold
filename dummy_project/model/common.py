from typing import Literal

from pydantic import Field, BaseModel
from typing_extensions import Annotated


sort_order_literal = Literal[
    "ascending",
    "descending",
]


class MetaMulti(BaseModel):
    result_size: Annotated[int, Field(gt=-1)]


class DataDelete(BaseModel):
    pass
