from abc import ABC, abstractmethod
from uuid import UUID

from src.core.ports.driving.forProcessingTrainUpdates.models.train_position import (
    TrainPosition,
)


class ForCachingTrainPosition(ABC):
    @abstractmethod
    async def cache(self, train_position: TrainPosition) -> None:
        pass

    @abstractmethod
    async def get(self, train_id: UUID) -> TrainPosition | None:
        pass

    @abstractmethod
    async def get_all(self) -> list[TrainPosition]:
        pass
