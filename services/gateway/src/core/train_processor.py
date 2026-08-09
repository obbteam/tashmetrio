from src.core.ports.driven.forBroadcastingTrainUpdates.for_broadcasting_train_updates import (
    ForBroadcastingTrainUpdates,
)
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
    def __init__(
        self,
        forCachingTrainUpdates: ForCachingTrainPosition,
        forBroadcastingTrainUpdates: ForBroadcastingTrainUpdates,
    ):
        self._for_caching_train_updates = forCachingTrainUpdates
        self._for_broadcasting_train_updates = forBroadcastingTrainUpdates

    async def process(self, train_position: TrainPosition) -> None:
        if train_position.is_finished == True:
            await self._for_caching_train_updates.delete(
                train_id=train_position.train_id
            )
            await self._for_broadcasting_train_updates.broadcast_finished(
                train_position=train_position
            )

        else:
            await self._for_caching_train_updates.cache(train_position=train_position)
            await self._for_broadcasting_train_updates.broadcast_position(
                train_position=train_position
            )
