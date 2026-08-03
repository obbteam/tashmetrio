from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel

from src.core.common.models.position import Position


class Trip(BaseModel):
    class TripStatus(StrEnum):
        ON_TIME = "ON TIME" 
        DELAYED = "DELAYED"
        CANCELLED = "CANCELLED"
        
    id: UUID
    train_id: UUID
    timetable_entry_id: UUID
    line_id: UUID
    
    departure_time: datetime
    estiamated_arrival_time: datetime
    
    trip_status: TripStatus
    current_segment_id: UUID
    progress_pct: float
    current_position: Position
    current_segment_time: datetime
    
    is_finished: bool
    
    updated_at: datetime
