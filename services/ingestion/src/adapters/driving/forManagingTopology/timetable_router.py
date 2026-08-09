from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter

from src.adapters.driving.forManagingTopology.models.update_timetable_request import (
    UpdateTimetableRequest,
)
from src.core.ports.driving.forManagingTopology.for_managing_topology import (
    ForManagingTopology,
)
from src.core.ports.driving.forManagingTopology.models.timetable_info import (
    TimetableInfo,
)

timetable_router = APIRouter(route_class=DishkaRoute)


@timetable_router.patch("/timetable/{timetable_entry_id}")
async def update(
    timetable_entry_id: UUID,
    update_time_table_request: UpdateTimetableRequest,
    for_managing_topology: FromDishka[ForManagingTopology],
) -> bool:
    return await for_managing_topology.update_timetable(
        new_timetable_info=TimetableInfo(
            timetable_id=timetable_entry_id,
            train_id=update_time_table_request.train_id,
            direction=update_time_table_request.direction,
            departure_time=update_time_table_request.departure_time,
        ),
    )


@timetable_router.get("/timetable")
async def get_all(
    for_managing_topology: FromDishka[ForManagingTopology],
) -> list[TimetableInfo]:
    return await for_managing_topology.get_timetable_entries()


__all__ = ["timetable_router"]
