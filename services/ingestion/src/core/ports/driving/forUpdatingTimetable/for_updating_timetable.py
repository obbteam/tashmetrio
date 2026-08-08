from abc import ABC, abstractmethod

from src.core.ports.driving.forUpdatingTimetable.models.timetable_info import (
    TimetableInfo,
)


class ForUpdatingTimetable(ABC):
    @abstractmethod
    async def update(self, new_timetable_info: TimetableInfo) -> bool:
        pass
    
    @abstractmethod
    async def get_all(self) -> list[TimetableInfo]:
        pass
