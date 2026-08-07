from uuid import UUID

from pydantic import BaseModel

from src.core.common.models.position import Position
from src.core.common.models.trip import Trip


class TrainPosition(BaseModel):
    trip_id: UUID
    train_id: UUID
    line_id: UUID

    current_segment_id: UUID
    progress_pct: float
    position: Position
    trip_status: Trip.TripStatus

    is_finished: bool
