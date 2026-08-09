from uuid import UUID

from geojson_pydantic import LineString, Point

from src.core.common.models.base import BaseModel


class StationInfo(BaseModel):
    station_id: UUID
    name: str
    sequence: int
    geom: Point


class LineStationInfo(BaseModel):
    line_id: UUID
    name: str
    color_hex: str
    geom: LineString
    stations: list[StationInfo]
