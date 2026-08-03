from abc import ABC, abstractmethod

from src.core.common.models.trip import Trip


class ForUpdatingTrip(ABC):
    @abstractmethod
    async def update(self, trip: Trip) -> bool:
        pass
