from dishka.integrations.fastapi import DishkaRoute, FromDishka, inject
from fastapi import APIRouter, WebSocket
from src.adapters.common.websocket.dependencies import ConnectionManager
from src.adapters.driving.forConnectingFrontend.models.train_position_snapshot import (
    TrainPositionData,
    TrainPositionSnapshot,
)
from src.core.ports.driving.forConnectingFrontend.for_connecting_frontend import (
    ForConnectingFrontend,
)

router = APIRouter(route_class=DishkaRoute)


@router.websocket("/train/positions")
@inject
async def websocket_endpoint(
    websocket: WebSocket,
    for_connecting_frontend: FromDishka[ForConnectingFrontend],
    manager: FromDishka[ConnectionManager],
):
    await manager.connect(websocket=websocket)
    try:
        data = await for_connecting_frontend.get_snapshot()
        await manager.send_snapshot(
            snapshot=TrainPositionSnapshot(
                snapshot_data=[TrainPositionData.model_validate(d) for d in data]
            ),
            websocket=websocket,
        )
        while True:
            data = await websocket.receive_json()
    finally:
        manager.disconnect(websocket=websocket)


__all__ = ["router"]
