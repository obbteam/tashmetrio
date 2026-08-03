from abc import ABC, abstractmethod
from uuid import UUID


class ForLookingUpNextSegment(ABC):
    @abstractmethod
    async def get_next_segment(self, line_id: UUID, current_segment_id: UUID) -> UUID | None:
        pass
