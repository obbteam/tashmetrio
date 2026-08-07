from src.adapters.common.events.event import Event
from src.core.ports.driven.forPublishingTrainPosition.models.train_position import (
    TrainPosition as TrainPositionChangedEventDate,
)
from src.settings import BrokerTopic


class TrainPositionChangedEvent(Event[TrainPositionChangedEventDate]):
    event_data: TrainPositionChangedEventDate
    event_version: int = 1

    @classmethod
    def get_event_type(cls) -> str:
        return f"{BrokerTopic.TRAINS_POSITIONS.value}"

    @classmethod
    def get_event_topic(cls) -> BrokerTopic:
        return BrokerTopic.TRAINS_POSITIONS
