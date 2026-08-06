
from src.core.common.exceptions import ErrorCodeEnum, LogicalException
from src.core.common.models.timetable import Timetable
from src.core.ports.driven.forLookingUpTimetable.for_looking_up_timetable import (
    ForLookingUpTimetable,
)
from src.core.ports.driven.forPersistingTimetable.for_persisting_timetable import (
    ForPersistingTimetable,
)
from src.core.ports.driving.forUpdatingTimetable.for_updating_timetable import (
    ForUpdatingTimetable,
)
from src.core.ports.driving.forUpdatingTimetable.models.timetable_info import (
    TimetableInfo,
)


class TimeTableService(ForUpdatingTimetable):
    def __init__(
        self,
        forPersistingTimetable: ForPersistingTimetable,
        forLookingUpTimetable: ForLookingUpTimetable,
    ):
        self.forPersistingTimetable = forPersistingTimetable
        self.forLookingUpTimetable = forLookingUpTimetable

    async def update(self, new_timetable_info: TimetableInfo) -> bool:
        old = await self.forLookingUpTimetable.get_timetable_by_id(id=new_timetable_info.timetable_id)
        # TODO should also check if the train is not booked at the new departure time
        # by getting all the trips and checking if the new departure time is not

        if old is None:
            raise LogicalException(
                http_code=404, error_code=ErrorCodeEnum.TIMETABLE_NOT_FOUND
            )

        result = await self.forPersistingTimetable.save(
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
