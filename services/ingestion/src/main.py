from dishka import Provider, Scope, make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.adapters.common.database_session import IDatabaseSession, get_database_session
from src.adapters.common.unit_of_work import IUnitOfWork, get_unit_of_work
from src.adapters.driven.forLookingUpStation.line_stations_repository import (
    LineStationsRepository,
)
from src.adapters.driven.forPersistingTimetable.timetable_repository import (
    TimetableRepository,
)
from src.adapters.driving.forManagingTopology.timetable_router import timetable_router
from src.adapters.driving.forManagingTopology.topology_router import topology_router
from src.core.ports.driven.forLookingUpStation.for_looking_up_station import (
    ForLookingUpStation,
)
from src.core.ports.driven.forPersistingTimetable.for_persisting_timetable import (
    ForPersistingTimetable,
)
from src.core.ports.driving.forManagingTopology.for_managing_topology import (
    ForManagingTopology,
)
from src.core.topology_service import TopologyService

origins = [
    "http://localhost",
    "http://localhost:5173"
]


def setup_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(timetable_router)
    app.include_router(topology_router)

    topology_service_provider = Provider(scope=Scope.REQUEST)

    topology_service_provider.provide(
        get_database_session, scope=Scope.REQUEST, provides=IDatabaseSession
    )
    topology_service_provider.provide(
        get_unit_of_work, scope=Scope.REQUEST, provides=IUnitOfWork
    )
    topology_service_provider.provide(
        LineStationsRepository, provides=ForLookingUpStation
    )
    topology_service_provider.provide(
        TimetableRepository, provides=ForPersistingTimetable
    )
    topology_service_provider.provide(TopologyService, provides=ForManagingTopology)

    container = make_async_container(topology_service_provider)

    setup_dishka(container=container, app=app)
    return app


app = setup_app()
