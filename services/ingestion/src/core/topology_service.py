from src.core.common.exceptions import ErrorCodeEnum, LogicalException
from src.core.common.models.line_station_info import LineStationInfo
from src.core.common.models.timetable import Timetable
from src.core.ports.driven.forLookingUpStation.for_looking_up_station import (
    ForLookingUpStation,
)
from src.core.ports.driven.forPersistingTimetable.for_persisting_timetable import (
    ForPersistingTimetable,
)
from src.core.ports.driving.forManagingTopology.for_managing_topology import (
    ForManagingTopology,
)
from src.core.ports.driving.forManagingTopology.models.timetable_info import (
    TimetableInfo,
)


class TopologyService(ForManagingTopology):
    def __init__(
        self,
        forPersistingTimetable: ForPersistingTimetable,
        forLookingUpStation: ForLookingUpStation,
    ):
        self._forPersistingTimetable = forPersistingTimetable
        self._forLookingUpStation = forLookingUpStation

    async def update_timetable(self, new_timetable_info: TimetableInfo) -> bool:
        old = await self._forPersistingTimetable.get_timetable_by_id(
            id=new_timetable_info.timetable_id
        )
        # TODO should also check if the train is not booked at the new departure time
        # by getting all the trips and checking if the new departure time is not

        if old is None:
            raise LogicalException(
                http_code=404, error_code=ErrorCodeEnum.TIMETABLE_NOT_FOUND
            )

        result = await self._forPersistingTimetable.save(
            Timetable(
                id=old.id,
                train_id=new_timetable_info.train_id or old.train_id,
                line_id=old.line_id,
                direction=new_timetable_info.direction or old.direction,
                departure_time=new_timetable_info.departure_time or old.departure_time,
            )
        )

        if result is False:
            raise LogicalException(
                http_code=500, error_code=ErrorCodeEnum.TIMETABLE_NOT_UPDATED
            )

        return result

    async def get_timetable_entries(self) -> list[TimetableInfo]:
        timetable_entries = await self._forPersistingTimetable.get_timetable()

        return [
            TimetableInfo(
                timetable_id=t.id,
                train_id=t.train_id,
                direction=t.direction,
                departure_time=t.departure_time,
            )
            for t in timetable_entries
        ]

    async def get_lines_and_stations(self) -> list[LineStationInfo]:
        return await self._forLookingUpStation.get_raw_topology()
