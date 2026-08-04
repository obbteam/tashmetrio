import time

from dishka import FromDishka

from src.core.ports.driving.forGeneratingTrips.for_generating_trip import (
    ForGeneratingTrip,
)


class TripGenerator:
    def __init__(
        self,
        for_generating_trip: FromDishka[ForGeneratingTrip],
    ):
        self._for_generating_trip = for_generating_trip

    async def run(self) -> None:
        while True:
            print("Generator started...")
            await self._for_generating_trip.generate()

            # sleep for 6 hours
            print("Generator sleeping...")
            time.sleep(60 * 60 * 6)
