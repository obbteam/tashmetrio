from dishka import Provider, Scope, make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI

from src.adapters.common.database_session import IDatabaseSession, get_database_session
from src.adapters.common.unit_of_work import IUnitOfWork, get_unit_of_work
from src.adapters.driven.forLookingUpTimetable.timetable_repository import (
    TimetableRepository as LookUpRepo,
)
from src.adapters.driven.forStoringTimetable.timetable_repository import (
    TimetableRepository as StoreRepo,
)
from src.adapters.driving.forUpdatingTimetable.timetable_update_router import (
    router as timetable_router,
)
from src.core.ports.driven.forLookingUpTimetable.for_looking_up_timetable import (
    ForLookingUpTimetable,
)
from src.core.ports.driven.forStoringTimetable.for_storing_timetable import (
    ForStoringTimetable,
)
from src.core.ports.driving.forUpdatingTimetable.for_updating_timetable import (
    ForUpdatingTimetable,
)
from src.core.timetable_service import TimeTableService


def setup_app() -> FastAPI:
    app = FastAPI()
    app.include_router(timetable_router)

    timetable_service_provider = Provider(scope=Scope.REQUEST)

    timetable_service_provider.provide(
        get_database_session, scope=Scope.REQUEST, provides=IDatabaseSession
    )
    timetable_service_provider.provide(
        get_unit_of_work, scope=Scope.REQUEST, provides=IUnitOfWork
    )

    timetable_service_provider.provide(LookUpRepo, provides=ForLookingUpTimetable)
    timetable_service_provider.provide(StoreRepo, provides=ForStoringTimetable)
    timetable_service_provider.provide(TimeTableService, provides=ForUpdatingTimetable)

    container = make_async_container(timetable_service_provider)

    setup_dishka(container=container, app=app)
    return app


app = setup_app()
