from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import aliased

from src.adapters.common.database_session import IDatabaseSession
from src.adapters.common.models import Lines, LineStations, Stations
from src.core.common.models.position import Position
from src.core.ports.driven.forCalculatingCurrentTrainPosition.for_calculating_current_train_position import (
    ForCalculatingCurrentTrainPosition,
)


class TrainPositionCalculator(ForCalculatingCurrentTrainPosition):
    def __init__(self, database_session: IDatabaseSession):
        self._database_session = database_session

    async def calculate(
        self, current_segment_id: UUID, next_segment_id: UUID, segment_progress: float
    ) -> Position | None:
        async with self._database_session:
            current_ls = aliased(LineStations)
            next_ls = aliased(LineStations)
            station_a = aliased(Stations)
            station_b = aliased(Stations)

            stmt = (
                select(
                    Lines.geom.label("line_geom"),
                    station_a.geom.label("station_a_geom"),
                    station_b.geom.label("station_b_geom"),
                )
                .select_from(current_ls)
                .join(station_a, station_a.id == current_ls.station_id)
                .join(Lines, Lines.id == current_ls.line_id)
                .join(next_ls, next_ls.line_id == Lines.id)
                .join(station_b, station_b.id == next_ls.station_id)
                .where(
                    current_ls.id == current_segment_id,
                    next_ls.id == next_segment_id,
                )
            )

            row = (await self._database_session.execute(stmt)).one_or_none()
            
            if row is None:
                return None

            frac_a = func.ST_LineLocatePoint(row.line_geom, row.station_a_geom)
            frac_b = func.ST_LineLocatePoint(row.line_geom, row.station_b_geom)
            frac = frac_a + (segment_progress / 100) * (frac_b - frac_a)
            point = func.ST_LineInterpolatePoint(row.line_geom, frac)

            latlon_stmt = select(
                func.ST_Y(point).label("latitude"),
                func.ST_X(point).label("longitude"),
            )

            position = (await self._database_session.execute(latlon_stmt)).one_or_none()
            
            if position is None:
                return None

            return Position(latitude=position.latitude, longitude=position.longitude)
