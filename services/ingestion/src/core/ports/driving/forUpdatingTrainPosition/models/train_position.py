from uuid import UUID

from pydantic import BaseModel


class TrainPosition(BaseModel):
    trip_id: UUID
    
    segment_progress_pct: float
