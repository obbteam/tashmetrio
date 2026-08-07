import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from src.adapters.common.events.event_publisher import IEventPublisher
from src.adapters.driven.forPublishingTrainPosition.models.train_position_event import (
    TrainPositionChangedEvent,
)
from src.core.ports.driven.forPublishingTrainPosition.for_publishing_train_position import (
    ForPublishingTrainPosition,
)
from src.core.ports.driven.forPublishingTrainPosition.models.train_position import (
    TrainPosition,
)


class TrainPositionBroker(ForPublishingTrainPosition):
    def __init__(self, event_publisher: IEventPublisher):
        self._event_publisher = event_publisher

    async def publish(self, train_position: TrainPosition) -> None:
            await self._event_publisher.publish(
                event=TrainPositionChangedEvent(
                    event_pk=uuid.uuid4(),
                    event_data=train_position,
                    emitted_at=datetime.now(tz=ZoneInfo(key="UTC")),
                )
            )
