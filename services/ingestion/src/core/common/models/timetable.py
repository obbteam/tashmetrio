from datetime import time
from uuid import UUID

from pydantic import BaseModel

from src.core.common.enums import Direction


class Timetable(BaseModel):
    id: UUID
    train_id: UUID
    line_id: UUID
    direction: Direction
    departure_time: time
