from uuid import UUID

from src.core.common.models.base import BaseModel


class TrainPosition(BaseModel):
    trip_id: UUID
    
    segment_progress_pct: float
