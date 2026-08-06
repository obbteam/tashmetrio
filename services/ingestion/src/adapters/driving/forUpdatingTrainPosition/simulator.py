import time
from datetime import datetime
from math import sqrt
from uuid import UUID
from zoneinfo import ZoneInfo

from dishka import FromDishka
from sqlalchemy import select

from src.adapters.common.database_session import IDatabaseSession
from src.adapters.common.models import Lines, LineStations, Trips
from src.core.common.models.trip import Trip
from src.core.ports.driving.forUpdatingTrainPosition.for_updating_train_position import (
    ForUpdatingTrainPosition,
)
from src.core.ports.driving.forUpdatingTrainPosition.models.train_position import (
    TrainPosition,
)
from src.settings import settings


class Simulator:
    def __init__(
        self,
        for_updating_train_position: FromDishka[ForUpdatingTrainPosition],
        database_session: IDatabaseSession,
    ):
        self._for_updating_train_position = for_updating_train_position
        self._database_session = database_session

    async def run(self) -> None:
        while True:
            trips = await self._get_active_trips()

            print(f"[info] Found {len(trips)} active trips")

            for t in trips:
                try:
                    elapsed_time = datetime.now(tz=ZoneInfo("UTC")) - t.current_segment_time

                    v_max, a = await self._get_train_speed(line_id=t.line_id)
                    distance = await self._get_segment_length(
                        current_segment_id=t.current_segment_id
                    )
                    
                    progress = (
                        self._apply_trapezoidal_velocity(
                            t=elapsed_time.seconds, v_max=v_max, a=a, distance=distance
                        )
                        / distance
                    ) * 100

                    await self._for_updating_train_position.update(
                        new_train_position=TrainPosition(
                            trip_id=t.id,
                            segment_progress_pct=progress,
                        )
                    )
                except Exception as exc:
                    print(f"[error] {exc}")
                    continue
            
            
            print(f"[info] Now sleep for {settings.SIMULATOR_SLEEP_TIME_S}...")

            time.sleep(settings.SIMULATOR_SLEEP_TIME_S)

    async def _get_active_trips(self) -> list[Trip]:
        async with self._database_session:
            current_time = datetime.now(tz=ZoneInfo("UTC"))
            q = select(Trips).where(
                Trips.departure_time < current_time, Trips.is_finished == False
            )

            rows = await self._database_session.execute(q)
            results = rows.scalars().all()

            if not results:
                return []

            return [Trip.model_validate(r) for r in results]

    async def _get_train_speed(self, line_id: UUID) -> tuple[float, float]:
        async with self._database_session:
            q = select(Lines.max_speed_mps, Lines.max_acceleration_mps2).where(
                Lines.id == line_id
            )

            row = await self._database_session.execute(q)
            result = row.first()

            if result is None:
                return (settings.DEFAULT_LINE_SPEED, settings.DEFAULT_LINE_ACCELERATION)

            max_speed, max_accel = result

            return (float(max_speed), float(max_accel))

    async def _get_segment_length(self, current_segment_id: UUID) -> float:
        async with self._database_session:
            q = select(LineStations.distance_to_next_m).where(
                LineStations.id == current_segment_id
            )

            row = await self._database_session.execute(q)
            result = row.scalar()

            if result is None:
                return settings.DEFAULT_LINE_LENGTH_M

            return float(result)

    def _apply_trapezoidal_velocity(
        self, t: float, v_max: float, a: float, distance: float
    ):
        a_dec = a - settings.DEFAULT_DECEL_BUFFER
        d_acc = (v_max * v_max) / (2 * a)
        d_dec = (v_max * v_max) / (2 * a_dec)

        d_cruise = distance - d_acc - d_dec

        v_top = v_max
        if d_cruise < 0:
            d_cruise = 0
            v_top = sqrt(distance * a)
            d_acc = (v_top * v_top) / (2*a)
            d_dec = (v_top * v_top) / (2 * a_dec)

        t_acc = v_top / a
        t_cruise = d_cruise / v_top
        t_dec = v_top / a_dec
        
        total_trip_time = t_acc + t_cruise + t_dec
        
        if t <= t_acc:
            return 0.5 * a * t * t
        elif t <= t_acc + t_cruise:
            return d_acc + v_top * (t - t_acc)
        elif t <= total_trip_time:
            t3 = t - t_acc - t_cruise
            return d_acc + d_cruise + v_top * t3 - 0.5 * a_dec * t3 * t3
        else:
            return distance
