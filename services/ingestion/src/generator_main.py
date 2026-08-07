import asyncio

from dishka import Provider, Scope, make_async_container

from src.adapters.common.database_session import IDatabaseSession, get_database_session
from src.adapters.common.unit_of_work import IUnitOfWork, get_unit_of_work
from src.adapters.driven.forCalculatingCurrentTrainPosition.train_position_calculator import (
    TrainPositionCalculator,
)
from src.adapters.driven.forLookingUpStation.line_stations_repository import (
    LineStationsRepository as StationLookupRepo,
)
from src.adapters.driven.forLookingUpTimetable.timetable_repository import (
    TimetableRepository as TimeTableLookUpRepo,
)
from src.adapters.driven.forLookingUpTrip.trip_repository import (
    TripRepository as TripLookUpRepo,
)
from src.adapters.driven.forPersistingTrip.trip_repository import (
    TripRepository,
)
from src.adapters.driving.forGeneratingTrips.trip_generator import TripGenerator
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
from src.core.ports.driving.forGeneratingTrips.for_generating_trip import (
    ForGeneratingTrip,
)
from src.core.trip_service import TripService


async def main():

    trip_service_provider = Provider(scope=Scope.APP)

    trip_service_provider.provide(
        get_database_session, scope=Scope.APP, provides=IDatabaseSession
    )
    trip_service_provider.provide(
        get_unit_of_work, scope=Scope.APP, provides=IUnitOfWork
    )

    trip_service_provider.provide(TripLookUpRepo, provides=ForLookingUpTrip)
    trip_service_provider.provide(TripRepository, provides=ForPersistingTrip)
    trip_service_provider.provide(StationLookupRepo, provides=ForLookingUpStation)
    trip_service_provider.provide(TimeTableLookUpRepo, provides=ForLookingUpTimetable)
    trip_service_provider.provide(
        TrainPositionCalculator, provides=ForCalculatingCurrentTrainPosition
    )
    trip_service_provider.provide(TripService, provides=ForGeneratingTrip)
    trip_service_provider.provide(TripGenerator)

    container = make_async_container(trip_service_provider)

    trip_generator = await container.get(TripGenerator)
    await trip_generator.run()


if __name__ == "__main__":
    asyncio.run(main())
