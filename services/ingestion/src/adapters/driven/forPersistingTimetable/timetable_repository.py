from typing import cast
from uuid import UUID

from sqlalchemy import CursorResult, select, update

from src.adapters.common.models import TimetableEntries
from src.adapters.common.unit_of_work import IUnitOfWork
from src.core.common.models.timetable import Timetable
from src.core.ports.driven.forPersistingTimetable.for_persisting_timetable import (
    ForPersistingTimetable,
)


class TimetableRepository(ForPersistingTimetable):
    def __init__(self, unit_of_work: IUnitOfWork):
        self._unit_of_work = unit_of_work

    async def save(self, time_table: Timetable):
        async with self._unit_of_work:
            stmt = (
                update(TimetableEntries)
                .values(
                    train_id=time_table.train_id,
                    departure_time=time_table.departure_time,
                    direction=time_table.direction,
                )
                .where(TimetableEntries.id == time_table.id)
            )

            session = self._unit_of_work.get_session()
            result = cast(CursorResult, await session.execute(stmt))
            await self._unit_of_work.commit()

            return result.rowcount == 1

    async def get_timetable_by_id(self, id: UUID) -> Timetable | None:
        async with self._unit_of_work.get_session() as database_session:
            q = select(TimetableEntries).where(TimetableEntries.id == id)

            rows = await database_session.execute(q)
            result = rows.scalar()

            if result is None:
                return None

            return Timetable.model_validate(result)

    async def get_timetable(self) -> list[Timetable]:
        async with self._unit_of_work.get_session() as database_session:
            q = select(TimetableEntries).order_by(TimetableEntries.departure_time)

            rows = await database_session.execute(q)
            results = rows.scalars().all()

            if not results:
                return []

            return [Timetable.model_validate(r) for r in results]
