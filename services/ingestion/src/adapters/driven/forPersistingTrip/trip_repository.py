from typing import cast

from sqlalchemy import CursorResult, insert, update

from src.adapters.common.models import Trips
from src.adapters.common.unit_of_work import IUnitOfWork
from src.core.common.models.trip import Trip
from src.core.ports.driven.forPersistingTrip.for_persisting_trip import (
    ForPersistingTrip,
)
from src.core.ports.driven.forPersistingTrip.models.new_trip import NewTrip


class TripRepository(ForPersistingTrip):
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
        
    async def save(self, new_trip: NewTrip):
            async with self._unit_of_work:
                stmt = insert(Trips).values(
                    train_id=new_trip.train_id,
                    timetable_entry_id=new_trip.timetable_entry_id,
                    line_id=new_trip.line_id,
                    departure_time=new_trip.departure_time,
                    estimated_arrival_time=new_trip.estimated_arrival_time,
                    trip_status=new_trip.trip_status,
                    current_segment_id=new_trip.current_segment_id,
                    progress_pct=new_trip.progress_pct,
                    current_position=new_trip.current_position.to_ewkt,
                    current_segment_time=new_trip.current_segment_time,
                    is_finished=new_trip.is_finished,
                )
    
                session = self._unit_of_work.get_session()
                result = cast(CursorResult, await session.execute(stmt))
                await self._unit_of_work.commit()
    
                return result.rowcount == 1
