from datetime import time
from uuid import UUID

from pydantic import BaseModel

from src.core.common.enums import Direction


class UpdateTimetableRequest(BaseModel):
    train_id: UUID | None
    direction: Direction | None
    departure_time: time | None
