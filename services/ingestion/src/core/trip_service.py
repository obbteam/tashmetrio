from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from src.core.common.exceptions import ErrorCodeEnum, LogicalException
from src.core.common.models.trip import Trip
from src.core.ports.driven.forCalculatingCurrentTrainPosition.for_calculating_current_train_position import (
    ForCalculatingCurrentTrainPosition,
)
from src.core.ports.driven.forLookingUpStation.for_looking_up_station import (
    ForLookingUpStation,
)
from src.core.ports.driven.forLookingUpTimetable.for_looking_up_timetable import (
    ForLookingUpTimetable,
)
from src.core.ports.driven.forLookingUpTrip.for_looking_up_trip import ForLookingUpTrip
from src.core.ports.driven.forPersistingTrip.for_persisting_trip import (
    ForPersistingTrip,
)
from src.core.ports.driven.forPersistingTrip.models.new_trip import NewTrip
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
        forUpdatingTrip: ForPersistingTrip,
        forLookingUpStation: ForLookingUpStation,
        forLookingUpTimetable: ForLookingUpTimetable,
        forPersistingTrip: ForPersistingTrip,
        forCalculatingTrainPosition: ForCalculatingCurrentTrainPosition,
    ):
        self.forLookingUpTrip = forLookingUpTrip
        self.forUpdatingTrip = forUpdatingTrip
        self.forLookingUpStation = forLookingUpStation
        self.forLookingUpTimetable = forLookingUpTimetable
        self.forPersistingTrip = forPersistingTrip
        self.forCalculatingTrainPosition = forCalculatingTrainPosition

    async def update(self, new_train_position: TrainPosition) -> bool:
        old = await self.forLookingUpTrip.get_trip_by_id(new_train_position.trip_id)

        if old is None:
            raise LogicalException(
                http_code=404, error_code=ErrorCodeEnum.TRIP_NOT_FOUND
            )

        current_segment = old.current_segment_id
        current_segment_time = old.current_segment_time
        new_progress = round(min(max(new_train_position.segment_progress_pct, 0.0), 100.0),2)

        at_boundary = new_progress >= 100

        if (
            not at_boundary
            and new_progress - old.progress_pct < settings.MIN_PROGRESS_THRESHOLD
        ):
            print(
                f"[info] Delta progress {new_progress - old.progress_pct} is too small. Doing nothing..."
            )
            return False

        next_segment = await self.forLookingUpStation.get_next_segment(
            line_id=old.line_id, current_segment_id=current_segment
        )

        if not at_boundary:
            is_finished = False
            new_position = (
                await self.forCalculatingTrainPosition.calculate(
                    current_segment_id=old.current_segment_id,
                    next_segment_id=next_segment,
                    segment_progress=new_train_position.segment_progress_pct,
                )
                if next_segment
                else old.current_position
            )
        elif next_segment:
            print(f"[update] state=ADVANCE_TO_NEXT_SEGMENT next={next_segment}")
            is_finished = False
            new_progress = 0
            current_segment = next_segment
            current_segment_time = datetime.now(tz=ZoneInfo("UTC"))
            station_info = await self.forLookingUpStation.get_station_by_id(
                current_segment_id=current_segment
            )
            if station_info is None:
                print(
                    "[warn] Intermediate station is none. Falling back to the old position"
                )
                new_position = old.current_position
            else:
                new_position = station_info.position

        else:
            print("[update] state=FINISHED")
            is_finished = True
            current_segment_time = datetime.now(tz=ZoneInfo("UTC"))
            final_station = await self.forLookingUpStation.get_station_by_id(
                current_segment_id=old.current_segment_id
            )
            if final_station is None:
                print("[warn] Final station is none. Falling back to the old position")
                new_position = old.current_position
            else:
                new_position = final_station.position

        # TODO calc new eta, trip status
        new_eta = old.estimated_arrival_time
        new_trip_status = old.trip_status

        result = await self.forUpdatingTrip.update(
            trip=Trip(
                id=old.id,
                train_id=old.train_id,
                line_id=old.line_id,
                timetable_entry_id=old.timetable_entry_id,
                departure_time=old.departure_time,
                estimated_arrival_time=new_eta,
                trip_status=new_trip_status,
                current_segment_id=current_segment,
                progress_pct=new_progress,
                current_position=new_position if new_position else old.current_position,
                updated_at=datetime.now(tz=ZoneInfo("UTC")),
                created_at=old.created_at,
                is_finished=is_finished,
                current_segment_time=current_segment_time,
            )
        )

        return result

    async def generate(self) -> None:
        tomorrow = datetime.now(tz=ZoneInfo("UTC")) + timedelta(days=1)

        timetable_entries = await self.forLookingUpTimetable.get_timetable()
        trips_for_tomorrow = await self.forLookingUpTrip.get_trips_by_date(
            timestamp=tomorrow
        )

        print(f"[info] Found {len(timetable_entries)} timetable entries")
        print(f"[info] Found {len(trips_for_tomorrow)} trips for tomorrow")

        for timetable_entry in timetable_entries:
            naive_dt = datetime.combine(
                date=tomorrow.date(), time=timetable_entry.departure_time
            )
            tashkent_dt = naive_dt.replace(tzinfo=ZoneInfo("Asia/Tashkent"))
            target_time = tashkent_dt.astimezone(ZoneInfo("UTC"))
            trip_exists = False

            for trip in trips_for_tomorrow:
                if trip.departure_time > target_time:
                    break

                if trip.departure_time == target_time:
                    trip_exists = True
                    break

            if trip_exists == False:
                stationInfo = await self.forLookingUpStation.get_start_station(
                    line_id=timetable_entry.line_id, direction=timetable_entry.direction
                )

                print(
                    f"[info] Generating a trip for {target_time} and {timetable_entry.departure_time}"
                )

                await self.forPersistingTrip.save(
                    new_trip=NewTrip(
                        train_id=timetable_entry.train_id,
                        timetable_entry_id=timetable_entry.id,
                        line_id=timetable_entry.line_id,
                        departure_time=target_time,
                        estimated_arrival_time=target_time
                        + timedelta(minutes=settings.DEFAULT_ETA_MINUTES),
                        trip_status=NewTrip.TripStatus.ON_TIME,
                        progress_pct=0,
                        current_segment_id=stationInfo.segment_id,
                        current_position=stationInfo.position,
                        current_segment_time=target_time,
                        is_finished=False,
                    )
                )
