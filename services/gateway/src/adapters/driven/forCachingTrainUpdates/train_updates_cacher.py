from uuid import UUID

from redis.asyncio import Redis
from src.core.ports.driven.forCachingTrainUpdates.for_caching_train_updates import (
    ForCachingTrainPosition,
)
from src.core.ports.driving.forProcessingTrainUpdates.models.train_position import (
    TrainPosition,
)

_KEY = "trains:positions"


class TrainUpdatesCacher(ForCachingTrainPosition):
    def __init__(self, redis: Redis):
        self._redis = redis

    async def cache(self, train_position: TrainPosition) -> None:
        await self._redis.hset(
            _KEY,
            str(train_position.train_id),
            train_position.model_dump_json(),
        )

    async def get(self, train_id: UUID) -> TrainPosition | None:
        raw = await self._redis.hget(_KEY, str(train_id))
        return TrainPosition.model_validate_json(raw) if raw else None

    async def get_all(self) -> list[TrainPosition]:
        raw = await self._redis.hgetall(_KEY)
        return [TrainPosition.model_validate_json(v) for v in raw.values()]

    async def forget(self, train_id: UUID) -> None:
        await self._redis.hdel(_KEY, str(train_id))
