from abc import ABC, abstractmethod
from uuid import UUID

from src.core.ports.driving.forUpdatingTimetable.models.timetable_info import (
    TimetableInfo,
)


class ForUpdatingTimetable(ABC):
    @abstractmethod
    async def update(self, timetable_id: UUID, timetable_info: TimetableInfo) -> bool:
        pass
