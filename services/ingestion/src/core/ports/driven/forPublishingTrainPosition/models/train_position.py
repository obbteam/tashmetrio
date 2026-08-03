
from uuid import UUID

from pydantic import BaseModel

from src.core.common.models.position import Position


class TrainPosition(BaseModel):
    trip_id: UUID
    new_position: Position
