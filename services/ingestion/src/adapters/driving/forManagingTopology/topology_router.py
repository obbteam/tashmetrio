from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter

from src.core.common.models.line_station_info import LineStationInfo
from src.core.ports.driving.forManagingTopology.for_managing_topology import (
    ForManagingTopology,
)

topology_router = APIRouter(route_class=DishkaRoute)


@topology_router.get("/topology")
async def get_all(
    for_managing_topology: FromDishka[ForManagingTopology],
) -> list[LineStationInfo]:
    return await for_managing_topology.get_lines_and_stations()


__all__ = ["topology_router"]
