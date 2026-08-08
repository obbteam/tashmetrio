import asyncio

from dishka import Provider, Scope, make_async_container
from dishka_faststream import setup_dishka
from redis.asyncio import Redis as AsyncRedis

import src.adapters.driving.forConsumingTrainUpdates.train_position_changed_event_handler  # noqa: F401
from src.adapters.common.events.dependencies import app
from src.adapters.common.redis.dependecies import get_redis_client
from src.adapters.driven.forCachingTrainUpdates.train_updates_cacher import (
    TrainUpdatesCacher,
)
from src.core.ports.driven.forCachingTrainUpdates.for_caching_train_updates import (
    ForCachingTrainPosition,
)
from src.core.ports.driving.forProcessingTrainUpdates.for_processing_train_updates import (
    ForProcessingTrainUpdates,
)
from src.core.train_processor import TrainProcessor


async def main():
    train_processor_provider = Provider(scope=Scope.APP)

    train_processor_provider.provide(
        get_redis_client, scope=Scope.APP, provides=AsyncRedis
    )
    train_processor_provider.provide(
        TrainUpdatesCacher, provides=ForCachingTrainPosition
    )
    train_processor_provider.provide(TrainProcessor, provides=ForProcessingTrainUpdates)

    container = make_async_container(train_processor_provider)

    setup_dishka(container=container, app=app, finalize_container=True, auto_inject=True)

    await app.run()


if __name__ == "__main__":
    asyncio.run(main())
