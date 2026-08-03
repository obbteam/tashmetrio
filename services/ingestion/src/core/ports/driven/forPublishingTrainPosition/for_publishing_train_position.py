from abc import ABC, abstractmethod

from src.core.ports.driven.forPublishingTrainPosition.models.train_position import (
    TrainPosition,
)


class ForPublishingTrainPosition(ABC):
    @abstractmethod
    def publish(self, train_position: TrainPosition) -> bool:
        pass
