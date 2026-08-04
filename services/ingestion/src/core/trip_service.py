from datetime import datetime, timedelta

from src.core.common.exceptions import ErrorCodeEnum, LogicalException
from src.core.common.models.trip import Trip
from src.core.ports.driven.forLookingUpStation.for_looking_up_station import (
    ForLookingUpStation,
)
from src.core.ports.driven.forLookingUpTimetable.for_looking_up_timetable import (
    ForLookingUpTimetable,
)
from src.core.ports.driven.forLookingUpTrip.for_looking_up_trip import ForLookingUpTrip
from src.core.ports.driven.forStoringTrip.for_storing_trip import ForStoringTrip
from src.core.ports.driven.forStoringTrip.models.new_trip import NewTrip
from src.core.ports.driven.forUpdatingTrip.for_updating_trip import ForUpdatingTrip
from src.core.ports.driving.forGeneratingTrips.for_generating_trip import (
    ForGeneratingTrip,
)
from src.core.ports.driving.forUpdatingTrainPosition.for_updating_train_position import (
    ForUpdatingTrainPosition,
)
from src.core.ports.driving.forUpdatingTrainPosition.models.train_position import (
    TrainPosition,
)
from src.settings import settings


class TripService(ForUpdatingTrainPosition, ForGeneratingTrip):
    def __init__(
        self,
        forLookingUpTrip: ForLookingUpTrip,
        forUpdatingTrip: ForUpdatingTrip,
        forLookingUpStation: ForLookingUpStation,
        forLookingUpTimetable: ForLookingUpTimetable,
        forStoringTrip: ForStoringTrip
    ):
        self.forLookingUpTrip = forLookingUpTrip
        self.forUpdatingTrip = forUpdatingTrip
        self.forLookingUpStation = forLookingUpStation
        self.forLookingUpTimetable = forLookingUpTimetable
        self.forStoringTrip = forStoringTrip

    async def update(self, new_train_position: TrainPosition) -> bool:
        old = await self.forLookingUpTrip.get_trip_by_id(new_train_position.trip_id)
        if old is None:
            raise LogicalException(
                http_code=404, error_code=ErrorCodeEnum.TRIP_NOT_FOUND
            )

        current_segment = old.current_segment_id
        current_segment_time = old.current_segment_time
        is_finished = False
        new_progress = new_train_position.segment_progress_pct
        

        if new_progress - old.progress_pct < settings.MIN_PROGRESS_THRESHOLD:
            return False

        if new_progress >= 100:
            next_segment = await self.forLookingUpStation.get_next_segment(
                line_id=old.line_id, current_segment_id=current_segment
            )

            new_progress = 0
            current_segment_time = datetime.now(tz=settings.TIME_ZONE)
            
            if next_segment is None:
                is_finished = True
            else:
                current_segment = next_segment


        # TODO calc new eta, trip status, position
        new_eta = old.estiamated_arrival_time
        new_trip_status = old.trip_status
        new_position = old.current_position

        result = await self.forUpdatingTrip.update(
            trip=Trip(
                id=old.id,
                train_id=old.train_id,
                line_id=old.line_id,
                timetable_entry_id=old.timetable_entry_id,
                departure_time=old.departure_time,
                estiamated_arrival_time=new_eta,
                trip_status=new_trip_status,
                current_segment_id=current_segment,
                progress_pct=new_progress,
                current_position=new_position,
                updated_at=datetime.now(tz=settings.TIME_ZONE),
                created_at=old.created_at,
                is_finished=is_finished,
                current_segment_time=current_segment_time
            )
        )

        return result

    async def generate(self) -> None:
        tomorrow = datetime.now(tz=settings.TIME_ZONE) + timedelta(days=1)
        
        timetable_entries = await self.forLookingUpTimetable.get_timetable()
        trips_for_tomorrow = await self.forLookingUpTrip.get_trips_by_date(timestamp=tomorrow)
        
        print(f"Found {len(timetable_entries)} timetable entries")
        print(f"Found {len(trips_for_tomorrow)} trips for tomorrow")
        
        for timetable_entry in timetable_entries:
            target_time = datetime.combine(date=tomorrow.date(), time=timetable_entry.departure_time)
            trip_exists = False
            
            for trip in trips_for_tomorrow:
                if trip.departure_time > target_time:
                    break
                
                if timetable_entry.departure_time == target_time:
                    trip_exists = True
                    break
            
            if trip_exists == False:
                stationInfo = await self.forLookingUpStation.get_start_station(line_id=timetable_entry.line_id, direction=timetable_entry.direction)
                
                print(f"Generating a trip for {target_time}")
                
                await self.forStoringTrip.store(new_trip=NewTrip(
                    train_id=timetable_entry.train_id,
                    timetable_entry_id=timetable_entry.id,
                    line_id= timetable_entry.line_id,
                    
                    departure_time=target_time,
                    estimated_arrival_time = target_time + timedelta(minutes=settings.DEFAULT_ETA_MINUTES),
                    
                    trip_status=NewTrip.TripStatus.ON_TIME,
                    progress_pct=0,
                    current_segment_id=stationInfo.segment_id,
                    current_position=stationInfo.position,
                    current_segment_time=target_time,
                    
                    is_finished=False,
                ))
        
                
                
            
        
        