from datetime import time
from uuid import UUID

from pydantic import BaseModel

from src.core.common.enums import Direction


class TrainPosition(BaseModel):
    train_id: UUID
    direction: Direction
    departure_time: time
