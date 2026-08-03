from abc import ABC, abstractmethod


class ForGeneratingTrip(ABC):
    @abstractmethod
    def generate() -> None:
        pass
