from uuid import UUID

from src.adapters.common.websocket.update import Update
from src.core.common.enums import TripStatus
from src.core.common.models.base import BaseModel
from src.core.common.models.position import Position


class TrainPositionData(BaseModel):
    trip_id: UUID
    train_id: UUID
    line_id: UUID

    current_segment_id: UUID
    progress_pct: float
    position: Position
    trip_status: TripStatus

    is_finished: bool


class TrainPostionUpdate(Update[TrainPositionData]):
    update_data: TrainPositionData
    update_type: str
