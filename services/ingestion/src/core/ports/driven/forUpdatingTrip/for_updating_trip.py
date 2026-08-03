from abc import ABC, abstractmethod

from src.core.ports.driven.forUpdatingTrip.models.trip import Trip


class ForUpdatingTrip(ABC):
    @abstractmethod
    def update(trip: Trip) -> bool:
        pass
