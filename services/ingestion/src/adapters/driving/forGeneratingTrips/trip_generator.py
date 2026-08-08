import asyncio

from dishka import FromDishka

from src.core.ports.driving.forGeneratingTrips.for_generating_trip import (
    ForGeneratingTrip,
)
from src.settings import settings


class TripGenerator:
    def __init__(
        self,
        for_generating_trip: FromDishka[ForGeneratingTrip],
    ):
        self._for_generating_trip = for_generating_trip

    async def run(self) -> None:
        while True:
            print("[info] Generator started...")
            await self._for_generating_trip.generate_trips_from_timetable()

            print(f"[info] Generator sleeping for {settings.GENERATOR_SLEEP_TIME_S}...")
            await asyncio.sleep(settings.GENERATOR_SLEEP_TIME_S)
    
    async def generate_test_trips(self) -> None:
        await self._for_generating_trip.generate_trips_from_now()
