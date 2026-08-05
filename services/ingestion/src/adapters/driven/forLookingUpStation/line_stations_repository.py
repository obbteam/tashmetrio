from uuid import UUID

from sqlalchemy import func, or_, select
from src.core.common.models.position import Position

from src.adapters.common.database_session import IDatabaseSession
from src.adapters.common.models import LineStations, Stations
from src.core.common.enums import Direction
from src.core.ports.driven.forLookingUpStation.for_looking_up_station import (
    ForLookingUpStation,
)
from src.core.ports.driven.forLookingUpStation.models.station_info import StationInfo


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

    async def get_start_station(
        self, line_id: UUID, direction: Direction
    ) -> StationInfo:
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

            return StationInfo(
                segment_id=row.LineStations.id,
                position=Position(latitude=row.latitude, longitude=row.longitude),
            )
