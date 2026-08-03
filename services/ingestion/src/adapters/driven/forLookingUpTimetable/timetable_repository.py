from uuid import UUID

from sqlalchemy import select

from src.adapters.common.database_session import IDatabaseSession
from src.adapters.common.models import TimetableEntries
from src.core.common.models.timetable import Timetable
from src.core.ports.driven.forLookingUpTimetable.for_looking_up_timetable import (
    ForLookingUpTimetable,
)


class TimetableRepository(ForLookingUpTimetable):
    def __init__(self, database_session: IDatabaseSession):
        self._database_session = database_session

    async def get_timetable_by_id(self, id: UUID) -> Timetable | None:
        async with self._database_session:
            q = select(TimetableEntries).where(TimetableEntries.id == id)

            rows = await self._database_session.execute(q)
            result = rows.scalar()

            if result is None:
                return None

            return Timetable.model_validate(result)

    async def get_timetable(self) -> list[Timetable]:
        async with self._database_session:
            q = select(TimetableEntries)

            rows = await self._database_session.execute(q)
            results = rows.scalars().all()

            if not results:
                return []

            return [Timetable.model_validate(r) for r in results]
