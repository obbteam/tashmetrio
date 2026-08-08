from abc import ABC, abstractmethod

from src.core.ports.driving.forProcessingTrainUpdates.models.train_position import (
    TrainPosition,
)


class ForProcessingTrainUpdates(ABC):
    @abstractmethod
    async def process(self, train_position: TrainPosition) -> None:
        pass
