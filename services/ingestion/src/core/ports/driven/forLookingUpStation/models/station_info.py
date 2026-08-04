from uuid import UUID

from pydantic import BaseModel

from src.core.common.models.position import Position


class StationInfo(BaseModel):
    segment_id: UUID
    position: Position
    