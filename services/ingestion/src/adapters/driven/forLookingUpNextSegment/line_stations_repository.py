from uuid import UUID

from sqlalchemy import select

from src.adapters.common.database_session import IDatabaseSession
from src.adapters.common.models import LineStations
from src.core.ports.driven.forLookingUpNextSegment.for_looking_up_next_segment import (
    ForLookingUpNextSegment,
)


class LineStationsRepository(ForLookingUpNextSegment):
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
