from uuid import UUID

from src.core.common.exceptions import ErrorCodeEnum, LogicalException
from src.core.ports.driven.forLookingUpTimetable.for_looking_up_timetable import (
    ForLookingUpTimetable,
)
from src.core.ports.driven.forStoringTimetable.for_storing_timetable import (
    ForStoringTimetable,
)
from src.core.ports.driven.forStoringTimetable.models.timetable import Timetable
from src.core.ports.driving.forUpdatingTimetable.for_updating_timetable import (
    ForUpdatingTimetable,
)
from src.core.ports.driving.forUpdatingTimetable.models.timetable_info import (
    TimetableInfo,
)

from src.core.ports.driving.forUpdatingTrainPosition.

class TripService(ForUp):
    def __init__(
        self,
        forStoringTimetable: ForStoringTimetable,
        forLookingUpTimetable: ForLookingUpTimetable,
    ):
        self.forStoringTimetable = forStoringTimetable
        self.forLookingUpTimetable = forLookingUpTimetable

    async def update(self, timetable_id: UUID, timetable_info: TimetableInfo) -> bool:
        old = await self.forLookingUpTimetable.get_timetable_by_id(id=timetable_id)
        # TODO should also check if the train is not booked at the new departure time
        # by getting all the trips and checking if the new departure time is not

        if old is None:
            raise LogicalException(
                http_code=404, error_code=ErrorCodeEnum.TIMETABLE_NOT_FOUND
            )

        result = await self.forStoringTimetable.store(
            Timetable(
                id=old.id,
                train_id=timetable_info.train_id or old.train_id,
                direction=timetable_info.direction or old.direction,
                departure_time=timetable_info.departure_time or old.departure_time,
            )
        )

        if result is False:
            raise LogicalException(
                http_code=500, error_code=ErrorCodeEnum.TIMETABLE_NOT_UPDATED
            )

        return result
