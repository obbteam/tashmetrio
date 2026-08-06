from datetime import datetime
from enum import StrEnum
from uuid import UUID

from src.core.common.models.base import BaseModel
from src.core.common.models.position import Position


class NewTrip(BaseModel):
    class TripStatus(StrEnum):
        ON_TIME = "ON TIME"
        DELAYED = "DELAYED"
        CANCELLED = "CANCELLED"

    train_id: UUID
    timetable_entry_id: UUID
    line_id: UUID

    departure_time: datetime
    estimated_arrival_time: datetime

    trip_status: TripStatus
    current_segment_id: UUID
    progress_pct: float
    current_position: Position
    current_segment_time: datetime

    is_finished: bool
