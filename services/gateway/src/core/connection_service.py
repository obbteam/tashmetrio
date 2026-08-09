from src.core.ports.driven.forCachingTrainUpdates.for_caching_train_updates import (
    ForCachingTrainPosition,
)
from src.core.ports.driving.forConnectingFrontend.for_connecting_frontend import (
    ForConnectingFrontend,
)
from src.core.ports.driving.forProcessingTrainUpdates.models.train_position import (
    TrainPosition,
)


class ConnectionService(ForConnectingFrontend):
    def __init__(self, forCachingTrainUpdates: ForCachingTrainPosition):
        self._forCachingTrainUpdates = forCachingTrainUpdates

    async def get_snapshot(self) -> list[TrainPosition]:
        return await self._forCachingTrainUpdates.get_all()
