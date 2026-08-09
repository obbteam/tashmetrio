import json
from abc import ABC
from typing import Generic, TypeVar

from pydantic import BaseModel, field_validator

TSnapshotData = TypeVar("TSnapshotData", bound=BaseModel)


class Snapshot(BaseModel, ABC, Generic[TSnapshotData]):
    snapshot_type: str
    snapshot_data: list[TSnapshotData]

    @classmethod
    def get_snapshot_type(cls) -> str:
        return cls.snapshot_type

    @field_validator("snapshot_data", mode="before")
    @classmethod
    def parse_snapshot_data(cls, value: str | list) -> list:
        if isinstance(value, str):
            return json.loads(value)

        return [json.loads(item) if isinstance(item, str) else item for item in value]
