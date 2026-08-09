from src.adapters.common.websocket.dependencies import ConnectionManager
from src.adapters.driven.forBroadcastingTrainUpdates.models.train_position_update import (
    TrainPositionData,
    TrainPostionUpdate,
)
from src.core.ports.driven.forBroadcastingTrainUpdates.for_broadcasting_train_updates import (
    ForBroadcastingTrainUpdates,
)
from src.core.ports.driving.forProcessingTrainUpdates.models.train_position import (
    TrainPosition,
)


class TrainUpdatesBroadcaster(ForBroadcastingTrainUpdates):
    def __init__(self, websocket_manager: ConnectionManager):
        self._websocket_manager = websocket_manager

    async def broadcast_position(self, train_position: TrainPosition) -> None:
        await self._websocket_manager.broadcast_update(
            update=TrainPostionUpdate(
                update_type="train_position_update",
                update_data=TrainPositionData.model_validate(train_position),
            )
        )

    async def broadcast_finished(self, train_position: TrainPosition) -> None:
        await self._websocket_manager.broadcast_update(
            update=TrainPostionUpdate(
                update_type="trip_finished",
                update_data=TrainPositionData.model_validate(train_position),
            )
        )
