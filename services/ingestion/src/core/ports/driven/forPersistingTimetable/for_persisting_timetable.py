from abc import ABC, abstractmethod
from uuid import UUID

from src.core.common.models.timetable import Timetable


class ForPersistingTimetable(ABC):
    @abstractmethod
    async def save(self, time_table: Timetable) -> bool:
        pass

    @abstractmethod
    async def get_timetable(self) -> list[Timetable]:
        pass

    @abstractmethod
    async def get_timetable_by_id(self, id: UUID) -> Timetable | None:
        pass
