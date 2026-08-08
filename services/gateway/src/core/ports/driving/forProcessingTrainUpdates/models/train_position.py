from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel
from src.core.common.models.position import Position


class TrainPosition(BaseModel):
    class TripStatus(StrEnum):
        ON_TIME = "ON TIME"
        DELAYED = "DELAYED"
        CANCELLED = "CANCELLED"

    trip_id: UUID
    train_id: UUID
    line_id: UUID

    current_segment_id: UUID
    progress_pct: float
    position: Position
    trip_status: TripStatus
    is_finished: bool

    emitted_at: datetime
