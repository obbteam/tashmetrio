from abc import ABC, abstractmethod
from uuid import UUID

from src.core.ports.driven.forLookingUpTimetable.models.timetable import Timetable


class ForLookingUpTimetable(ABC):
    @abstractmethod
    async def get_timetable(self) -> list[Timetable]:
        pass

    @abstractmethod
    async def get_timetable_by_id(self, id: UUID) -> Timetable | None:
        pass
