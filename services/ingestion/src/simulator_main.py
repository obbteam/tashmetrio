import asyncio

from dishka import Provider, Scope, make_async_container

from src.adapters.common.database_session import IDatabaseSession, get_database_session
from src.adapters.common.unit_of_work import IUnitOfWork, get_unit_of_work
from src.adapters.driven.forLookingUpNextSegment.line_stations_repository import (
    LineStationsRepository as NextSegmentLookUpRepo,
)
from src.adapters.driven.forLookingUpTrip.trip_repository import (
    TripRepository as TripLookUpRepo,
)
from src.adapters.driven.forUpdatingTrip.trip_repository import (
    TripRepository as TripUpdateRepo,
)
from src.adapters.driving.forUpdatingTrainPosition.simulator import Simulator
from src.core.ports.driven.forLookingUpNextSegment.for_looking_up_next_segment import (
    ForLookingUpNextSegment,
)
from src.core.ports.driven.forLookingUpTrip.for_looking_up_trip import ForLookingUpTrip
from src.core.ports.driven.forUpdatingTrip.for_updating_trip import ForUpdatingTrip
from src.core.ports.driving.forUpdatingTrainPosition.for_updating_train_position import (
    ForUpdatingTrainPosition,
)
from src.core.trip_service import TripService


async def main():
    trip_service_provider = Provider(scope=Scope.APP)
        
    trip_service_provider.provide(get_database_session, scope=Scope.APP, provides=IDatabaseSession)
    trip_service_provider.provide(
        get_unit_of_work, scope=Scope.APP, provides=IUnitOfWork
    )

    trip_service_provider.provide(TripLookUpRepo,provides= ForLookingUpTrip)
    trip_service_provider.provide(TripUpdateRepo, provides=ForUpdatingTrip)
    trip_service_provider.provide(NextSegmentLookUpRepo, provides=ForLookingUpNextSegment)
    
    trip_service_provider.provide(TripService, provides=ForUpdatingTrainPosition)
    trip_service_provider.provide(Simulator)
    
    container = make_async_container(trip_service_provider)
    
    simulator = await container.get(Simulator)
    await simulator.run()
    
    
if __name__ == "__main__":
    asyncio.run(main())