from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter

from src.adapters.driving.forUpdatingTimetable.models.update_timetable_request import (
    UpdateTimetableRequest,
)
from src.core.ports.driving.forUpdatingTimetable.for_updating_timetable import (
    ForUpdatingTimetable,
)
from src.core.ports.driving.forUpdatingTimetable.models.timetable_info import (
    TimetableInfo,
)

router = APIRouter(route_class=DishkaRoute)


@router.patch("/timetable/{timetable_entry_id}")
async def update(
    timetable_entry_id: UUID,
    update_time_table_request: UpdateTimetableRequest,
    for_updating_timetable: FromDishka[ForUpdatingTimetable],
) -> bool:
    return await for_updating_timetable.update(
        new_timetable_info=TimetableInfo(
            timetable_id=timetable_entry_id,
            train_id=update_time_table_request.train_id,
            direction=update_time_table_request.direction,
            departure_time=update_time_table_request.departure_time,
        ),
    )


__all__ = ["router"]
