from src.core.ports.driven.forCachingTrainUpdates.for_caching_train_updates import (
    ForCachingTrainPosition,
)
from src.core.ports.driving.forProcessingTrainUpdates.for_processing_train_updates import (
    ForProcessingTrainUpdates,
)
from src.core.ports.driving.forProcessingTrainUpdates.models.train_position import (
    TrainPosition,
)


class TrainProcessor(ForProcessingTrainUpdates):
    def __init__(self, forCachingTrainUpdates: ForCachingTrainPosition):
        self._forCachingTrainUpdates = forCachingTrainUpdates

    async def process(self, train_position: TrainPosition) -> None:
        await self._forCachingTrainUpdates.cache(train_position=train_position)
