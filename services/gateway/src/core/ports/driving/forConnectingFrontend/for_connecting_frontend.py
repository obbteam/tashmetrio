from abc import ABC, abstractmethod

from src.core.ports.driving.forProcessingTrainUpdates.models.train_position import (
    TrainPosition,
)


class ForConnectingFrontend(ABC):
    @abstractmethod
    async def get_snapshot(self) -> list[TrainPosition]:
        pass
