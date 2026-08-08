import json
import uuid
from abc import ABC
from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

TEventData = TypeVar("TEventData", bound=BaseModel)


class Event(BaseModel, Generic[TEventData], ABC):
    event_pk: UUID = Field(default_factory=uuid.uuid4)
    event_version: int = Field(gt=0)
    event_data: TEventData
    emitted_at: datetime

    @classmethod
    def get_event_type(cls) -> str:
        raise NotImplementedError()

    @classmethod
    def get_event_topic(cls) -> str:
        raise NotImplementedError()

    def get_headers(self) -> dict[str, str]:
        return {
            "event_pk": str(self.event_pk),
            "event_type": self.get_event_type(),
            "event_version": str(self.event_version),
            "emitted_at": str(self.emitted_at)
        }

    @field_validator("event_data", mode="before")
    @classmethod
    def parse_event_data(cls, value: str | TEventData) -> TEventData:
        if isinstance(value, str):
            return json.loads(value)

        return value
    