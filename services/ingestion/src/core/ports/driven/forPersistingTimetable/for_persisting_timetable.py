from abc import ABC, abstractmethod

from src.core.common.models.timetable import Timetable


class ForPersistingTimetable(ABC):
    @abstractmethod
    async def save(self, time_table: Timetable) -> bool:
        pass
