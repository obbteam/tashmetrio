from abc import ABC, abstractmethod

from src.core.ports.driving.forUpdatingTrainPosition.models.train_position import (
    TrainPosition,
)


class ForUpdatingTrainPosition(ABC):
    @abstractmethod
    def update(self, new_train_position: TrainPosition) -> bool:
        pass
