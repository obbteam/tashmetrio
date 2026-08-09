from uuid import UUID

from src.adapters.common.websocket.snapshot import Snapshot
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


class TrainPositionSnapshot(Snapshot[TrainPositionData]):
    snapshot_data: list[TrainPositionData]
    snapshot_type: str = "train_position_snapshot"
