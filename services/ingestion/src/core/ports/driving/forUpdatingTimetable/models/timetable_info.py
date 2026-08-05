from datetime import time
from uuid import UUID

from src.core.common.enums import Direction
from src.core.common.models.base import BaseModel


class TimetableInfo(BaseModel):
    timetable_id: UUID
    
    train_id: UUID | None
    direction: Direction | None
    departure_time: time | None
