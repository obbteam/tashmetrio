from typing import cast

from sqlalchemy import CursorResult, update

from src.adapters.common.models import TimetableEntries
from src.adapters.common.unit_of_work import IUnitOfWork
from src.core.common.models.timetable import Timetable
from src.core.ports.driven.forStoringTimetable.for_storing_timetable import (
    ForStoringTimetable,
)


class TimetableRepository(ForStoringTimetable):
    def __init__(self, unit_of_work: IUnitOfWork):
        self._unit_of_work = unit_of_work

    async def store(self, time_table: Timetable):
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
