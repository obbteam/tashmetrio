from abc import ABC, abstractmethod

from src.core.ports.driving.forProcessingTrainUpdates.models.train_position import (
    TrainPosition,
)


class ForBroadcastingTrainUpdates(ABC):
    @abstractmethod
    async def broadcast_position(self, train_position: TrainPosition) -> None:
        pass
    
    @abstractmethod
    async def broadcast_finished(self, train_position: TrainPosition) -> None:
        pass
