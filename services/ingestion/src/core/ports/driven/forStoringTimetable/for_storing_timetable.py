from abc import ABC, abstractmethod

from src.core.common.models.timetable import Timetable


class ForStoringTimetable(ABC):
    @abstractmethod
    async def store(self, time_table: Timetable) -> bool:
        pass
