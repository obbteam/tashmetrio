from abc import ABC, abstractmethod
from uuid import UUID

from src.core.common.models.trip import Trip


class ForLookingUpTrip(ABC):
    @abstractmethod
    async def get_trips(self) -> list[Trip]:
        pass

    @abstractmethod
    async def get_trip_by_id(self, id: UUID) -> Trip | None:
        pass
