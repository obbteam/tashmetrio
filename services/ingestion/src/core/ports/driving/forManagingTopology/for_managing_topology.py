from abc import ABC, abstractmethod

from src.core.common.models.line_station_info import (
    LineStationInfo,
)
from src.core.ports.driving.forManagingTopology.models.timetable_info import (
    TimetableInfo,
)


class ForManagingTopology(ABC):
    @abstractmethod
    async def update_timetable(self, new_timetable_info: TimetableInfo) -> bool:
        pass
    
    @abstractmethod
    async def get_timetable_entries(self) -> list[TimetableInfo]:
        pass
    
    @abstractmethod
    async def get_lines_and_stations(self) -> list[LineStationInfo]:
        pass
    
    
