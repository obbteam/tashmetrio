import time

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
            await self._for_generating_trip.generate()

            print(f"[info] Generator sleeping for {settings.GENERATOR_SLEEP_TIME_S}...")
            time.sleep(settings.GENERATOR_SLEEP_TIME_S)
