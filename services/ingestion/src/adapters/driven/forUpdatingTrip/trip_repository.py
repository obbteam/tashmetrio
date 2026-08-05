from typing import cast

from sqlalchemy import CursorResult, update

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
                    estimated_arrival_time=trip.estimated_arrival_time,
                    
                    trip_status=trip.trip_status,
                    current_segment_id=trip.current_segment_id,
                    progress_pct=trip.progress_pct,
                    current_position=trip.current_position.to_ewkt,
                    current_segment_time=trip.current_segment_time,
                    
                    is_finished=trip.is_finished,
                    updated_at=trip.updated_at,
                )
                .where(Trips.id == trip.id)
            )

            session = self._unit_of_work.get_session()
            result = cast(CursorResult, await session.execute(stmt))
            await self._unit_of_work.commit()

            return result.rowcount == 1 
