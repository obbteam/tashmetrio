from abc import ABC, abstractmethod
from uuid import UUID

from src.core.common.models.position import Position


class ForCalculatingCurrentTrainPosition(ABC):
    @abstractmethod
    async def calculate(
        self, current_segment_id: UUID, next_segment_id: UUID, segment_progress: float
    ) -> Position | None:
        pass
