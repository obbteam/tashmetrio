from abc import ABC, abstractmethod


class ForGeneratingTrip(ABC):
    @abstractmethod
    async def generate(self) -> None:
        pass
