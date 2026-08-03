from uuid import UUID

from sqlalchemy import select

from src.adapters.common.database_session import IDatabaseSession
from src.adapters.common.models import Trips
from src.core.common.models.trip import Trip
from src.core.ports.driven.forLookingUpTrip.for_looking_up_trip import (
    ForLookingUpTrip,
)


class TripRepository(ForLookingUpTrip):
    def __init__(self, database_session: IDatabaseSession):
        self._database_session = database_session

    async def get_trip_by_id(self, id: UUID) -> Trip | None:
        async with self._database_session:
            q = select(Trips).where(Trips.id == id)

            rows = await self._database_session.execute(q)
            result = rows.scalar()

            if result is None:
                return None

            return Trip.model_validate(result)

    async def get_trips(self) -> list[Trip]:
        async with self._database_session:
            q = select(Trips)

            rows = await self._database_session.execute(q)
            results = rows.scalars().all()

            if not results:
                return []

            return [Trip.model_validate(r) for r in results]
