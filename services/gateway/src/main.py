import asyncio

import uvicorn
from dishka import Provider, Scope, make_async_container
from dishka.integrations.fastapi import setup_dishka as fastapi_setup_dishka
from dishka_faststream import setup_dishka as faststream_setup_dishka
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from faststream import FastStream
from redis.asyncio import Redis as AsyncRedis

import src.adapters.driving.forConsumingTrainUpdates.train_position_changed_event_handler  # noqa: F401
from src.adapters.common.events.dependencies import broker
from src.adapters.common.redis.dependecies import get_redis_client
from src.adapters.common.websocket.dependencies import (
    ConnectionManager,
    get_websocket_manager,
)
from src.adapters.driven.forBroadcastingTrainUpdates.train_updates_broadcaster import (
    TrainUpdatesBroadcaster,
)
from src.adapters.driven.forCachingTrainUpdates.train_updates_cacher import (
    TrainUpdatesCacher,
)
from src.adapters.driving.forConnectingFrontend.websocket_router import router
from src.core.connection_service import ConnectionService
from src.core.ports.driven.forBroadcastingTrainUpdates.for_broadcasting_train_updates import (
    ForBroadcastingTrainUpdates,
)
from src.core.ports.driven.forCachingTrainUpdates.for_caching_train_updates import (
    ForCachingTrainPosition,
)
from src.core.ports.driving.forConnectingFrontend.for_connecting_frontend import (
    ForConnectingFrontend,
)
from src.core.ports.driving.forProcessingTrainUpdates.for_processing_train_updates import (
    ForProcessingTrainUpdates,
)
from src.core.train_processor import TrainProcessor

origins = [
    "http://localhost",
    "http://localhost:5173"
]


def build_gateway_provier() -> Provider:
    provider = Provider(scope=Scope.APP)

    provider.provide(get_redis_client, scope=Scope.APP, provides=AsyncRedis)
    provider.provide(get_websocket_manager, scope=Scope.APP, provides=ConnectionManager)

    provider.provide(TrainUpdatesCacher, provides=ForCachingTrainPosition)
    provider.provide(TrainUpdatesBroadcaster, provides=ForBroadcastingTrainUpdates)
    provider.provide(TrainProcessor, provides=ForProcessingTrainUpdates)
    provider.provide(ConnectionService, provides=ForConnectingFrontend)

    return provider


async def main():
    container = make_async_container(build_gateway_provier())

    faststream_app = FastStream(broker)

    fastapi_app = FastAPI()
    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    fastapi_app.include_router(router=router)

    faststream_setup_dishka(
        container=container,
        app=faststream_app,
        auto_inject=True,
        finalize_container=True,
    )

    fastapi_setup_dishka(container=container, app=fastapi_app)

    config = uvicorn.Config(fastapi_app, host="0.0.0.0", port=8000)
    server = uvicorn.Server(config)

    await asyncio.gather(faststream_app.run(), server.serve())


if __name__ == "__main__":
    asyncio.run(main())
