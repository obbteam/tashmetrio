from abc import ABC, abstractmethod
from uuid import UUID

from src.core.ports.driven.forPublishingTrainPosition.models.train_position import (
    TrainPosition,
)


class ForPublishingTrainPosition(ABC):
    @abstractmethod
    def publish(trip_id: UUID, train_id: UUID, train_position: TrainPosition) -> bool:
        pass
