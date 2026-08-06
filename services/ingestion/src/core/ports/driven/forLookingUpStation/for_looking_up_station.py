from abc import ABC, abstractmethod
from uuid import UUID

from src.core.common.enums import Direction
from src.core.ports.driven.forLookingUpStation.models.station_info import StationInfo


class ForLookingUpStation(ABC):
    @abstractmethod
    async def get_next_segment(self, line_id: UUID, current_segment_id: UUID) -> UUID | None:
        pass
    
    @abstractmethod
    async def get_station_by_id(self, current_segment_id: UUID) -> StationInfo | None:
        pass
    
    @abstractmethod
    async def get_start_station(self, line_id: UUID, direction: Direction) -> StationInfo:
        pass
