from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from src.core.common.models.trip import Trip


class ForLookingUpTrip(ABC):
    @abstractmethod
    async def get_trips_by_date(self, timestamp: datetime) -> list[Trip]:
        pass

    @abstractmethod
    async def get_trip_by_id(self, id: UUID) -> Trip | None:
        pass
