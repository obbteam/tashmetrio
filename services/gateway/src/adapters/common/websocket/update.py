import json
from abc import ABC
from typing import Generic, TypeVar

from pydantic import BaseModel, field_validator

TUpdateData = TypeVar("TUpdateData", bound=BaseModel)


class Update(BaseModel, ABC, Generic[TUpdateData]):
    update_type: str
    update_data: TUpdateData

    @classmethod
    def get_update_type(cls) -> str:
        return cls.update_type

    @field_validator("update_data", mode="before")
    @classmethod
    def parse_update_data(cls, value: str | TUpdateData) -> TUpdateData:
        if isinstance(value, str):
            return json.loads(value)

        return value
