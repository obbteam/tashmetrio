from abc import ABC, abstractmethod

from src.core.ports.driven.forStoringTrip.models.new_trip import NewTrip


class ForStoringTrip(ABC):
    @abstractmethod
    async def store(self, new_trip: NewTrip) -> bool:
        pass
