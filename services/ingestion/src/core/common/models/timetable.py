from datetime import time
from uuid import UUID

from src.core.common.enums import Direction
from src.core.common.models.base import BaseModel


class Timetable(BaseModel):
    id: UUID
    train_id: UUID
    line_id: UUID
    direction: Direction
    departure_time: time
