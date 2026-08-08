from abc import ABC, abstractmethod


class ForGeneratingTrip(ABC):
    @abstractmethod
    async def generate_trips_from_timetable(self) -> None:
        pass
    
    @abstractmethod
    async def generate_trips_from_now(self) -> None:
        pass
