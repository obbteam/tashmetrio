from abc import ABC, abstractmethod

from src.core.common.models.trip import Trip
from src.core.ports.driven.forPersistingTrip.models.new_trip import NewTrip


class ForPersistingTrip(ABC):
    @abstractmethod
    async def update(self, trip: Trip) -> bool:
        pass
    
    @abstractmethod
    async def save(self, new_trip: NewTrip) -> bool:
            pass
