from collections import defaultdict
from uuid import UUID

from geojson_pydantic import LineString, Point
from sqlalchemy import func, or_, select
from src.adapters.common.database_session import IDatabaseSession
from src.adapters.common.models import Lines, LineStations, Stations
from src.core.common.enums import Direction
from src.core.common.models.line_station_info import (
    LineStationInfo,
    StationInfo,
)
from src.core.common.models.position import Position
from src.core.ports.driven.forLookingUpStation.for_looking_up_station import (
    ForLookingUpStation,
)
from src.core.ports.driven.forLookingUpStation.models.station_info import (
    StationInfo as SegmentInfo,
)


class LineStationsRepository(ForLookingUpStation):
    def __init__(self, database_session: IDatabaseSession):
        self._database_session = database_session

    async def get_next_segment(
        self, line_id: UUID, current_segment_id: UUID
    ) -> UUID | None:
        async with self._database_session:
            current_seq = (
                select(LineStations.sequence)
                .where(LineStations.id == current_segment_id)
                .scalar_subquery()
            )

            stmt = select(LineStations.id).where(
                LineStations.line_id == line_id,
                LineStations.sequence == current_seq + 1,
            )

            row = await self._database_session.execute(stmt)
            result = row.scalar()

            return result

    async def get_station_by_id(self, current_segment_id: UUID) -> SegmentInfo | None:
        async with self._database_session:
            stmt = (
                select(
                    LineStations,
                    func.ST_Y(Stations.geom).label("latitude"),
                    func.ST_X(Stations.geom).label("longitude"),
                )
                .join(Stations, LineStations.station_id == Stations.id)
                .where(
                    LineStations.id == current_segment_id,
                )
            )

            row = (await self._database_session.execute(stmt)).one_or_none()

            if row is None:
                return None

            return SegmentInfo(
                segment_id=row.LineStations.id,
                position=Position(latitude=row.latitude, longitude=row.longitude),
            )

    async def get_start_station(
        self, line_id: UUID, direction: Direction
    ) -> SegmentInfo:
        async with self._database_session:
            min_max_subq = (
                select(
                    func.min(LineStations.sequence).label("min_seq"),
                    func.max(LineStations.sequence).label("max_seq"),
                )
                .where(
                    LineStations.line_id == line_id,
                )
                .subquery()
            )

            stmt = (
                select(
                    LineStations,
                    func.ST_Y(Stations.geom).label("latitude"),
                    func.ST_X(Stations.geom).label("longitude"),
                )
                .join(Stations, LineStations.station_id == Stations.id)
                .where(
                    LineStations.line_id == line_id,
                    or_(
                        LineStations.sequence == min_max_subq.c.min_seq,
                        LineStations.sequence == min_max_subq.c.max_seq,
                    ),
                )
                .order_by(LineStations.sequence)
            )

            rows = await self._database_session.execute(stmt)
            results = rows.all()

            row = results[0] if direction == Direction.FORWARD else results[1]

            return SegmentInfo(
                segment_id=row.LineStations.id,
                position=Position(latitude=row.latitude, longitude=row.longitude),
            )

    async def get_raw_topology(self) -> list[LineStationInfo]:
        async with self._database_session:
            q = select(
                Lines.id,
                Lines.name,
                Lines.color_hex,
                func.ST_AsGeoJSON(Lines.geom).label("geom"),
            )

            rows = await self._database_session.execute(q)
            lines = rows.all()

            q = (
                select(
                    Stations.id,
                    Stations.name,
                    func.ST_AsGeoJSON(Stations.geom).label("geom"),
                    LineStations.line_id,
                    LineStations.sequence,
                )
                .join(LineStations, LineStations.station_id == Stations.id)
                .order_by(LineStations.line_id, LineStations.sequence)
            )

            rows = await self._database_session.execute(q)
            stations = rows.all()

            stations_by_line: dict[UUID, list[StationInfo]] = defaultdict(list)

            for s in stations:
                stations_by_line[s.line_id].append(
                    StationInfo(
                        station_id=s.id,
                        name=s.name,
                        sequence=s.sequence,
                        geom=Point.model_validate_json(s.geom),
                    )
                )

            result = [
                LineStationInfo(
                    line_id=l.id,
                    name=l.name,
                    color_hex=l.color_hex,
                    geom=LineString.model_validate_json(l.geom),
                    stations=stations_by_line.get(l.id, []),
                )
                for l in lines
            ]

            return result
