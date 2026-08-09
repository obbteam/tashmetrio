from uuid import UUID

from src.adapters.common.events.event import Event
from src.core.common.enums import TripStatus
from src.core.common.models.base import BaseModel
from src.core.common.models.position import Position
from src.settings import BrokerTopic


class TrainPositionChangedEventData(BaseModel):
    trip_id: UUID
    train_id: UUID
    line_id: UUID

    current_segment_id: UUID
    progress_pct: float
    position: Position
    trip_status: TripStatus

    is_finished: bool


class TrainPositionChangedEvent(Event[TrainPositionChangedEventData]):
    event_data: TrainPositionChangedEventData
    event_version: int = 1

    @classmethod
    def get_event_type(cls) -> str:
        return f"{BrokerTopic.TRAINS_POSITIONS.value}"

    @classmethod
    def get_event_topic(cls) -> BrokerTopic:
        return BrokerTopic.TRAINS_POSITIONS
