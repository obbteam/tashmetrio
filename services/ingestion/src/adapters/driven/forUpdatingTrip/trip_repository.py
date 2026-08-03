from sqlalchemy import update

from src.adapters.common.models import Trips
from src.adapters.common.unit_of_work import IUnitOfWork
from src.core.common.models.trip import Trip
from src.core.ports.driven.forUpdatingTrip.for_updating_trip import ForUpdatingTrip


class TripRepository(ForUpdatingTrip):
    def __init__(self, unit_of_work: IUnitOfWork):
        self._unit_of_work = unit_of_work

    async def update(self, trip: Trip) -> bool:
        async with self._unit_of_work:
            stmt = (
                update(Trips)
                .values(
                    current_position=trip.current_position,
                    estimated_arrival_time=trip.estiamated_arrival_time,
                    trip_status=trip.trip_status,
                    current_segment_id=trip.current_segment_id,
                    progress_pct=trip.progress_pct,
                    udated_at=trip.updated_at,
                )
                .where(Trips.id == trip.id)
            )

            session = self._unit_of_work.get_session()
            result = await session.execute(stmt)
            await self._unit_of_work.commit()

            return result.scalars().all().count == 1
