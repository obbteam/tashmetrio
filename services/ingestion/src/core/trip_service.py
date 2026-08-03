from datetime import datetime

from src.core.common.exceptions import ErrorCodeEnum, LogicalException
from src.core.common.models.trip import Trip
from src.core.ports.driven.forLookingUpNextSegment.for_looking_up_next_segment import (
    ForLookingUpNextSegment,
)
from src.core.ports.driven.forLookingUpTrip.for_looking_up_trip import ForLookingUpTrip
from src.core.ports.driven.forUpdatingTrip.for_updating_trip import ForUpdatingTrip
from src.core.ports.driving.forUpdatingTrainPosition.for_updating_train_position import (
    ForUpdatingTrainPosition,
)
from src.core.ports.driving.forUpdatingTrainPosition.models.train_position import (
    TrainPosition,
)
from src.settings import settings


class TripService(ForUpdatingTrainPosition):
    def __init__(
        self,
        forLookingUpTrip: ForLookingUpTrip,
        forUpdatingTrip: ForUpdatingTrip,
        forLookingUpNextSegment: ForLookingUpNextSegment,
    ):
        self.forLookingUpTrip = forLookingUpTrip
        self.forUpdatingTrip = forUpdatingTrip
        self.forLookingUpNextSegment = forLookingUpNextSegment

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
            next_segment = await self.forLookingUpNextSegment.get_next_segment(
                line_id=old.line_id, current_segment_id=current_segment
            )

            new_progress = 0
            current_segment_time = datetime.now()
            
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
                updated_at=datetime.now(),
                is_finished=is_finished,
                current_segment_time=current_segment_time
            )
        )

        return result
