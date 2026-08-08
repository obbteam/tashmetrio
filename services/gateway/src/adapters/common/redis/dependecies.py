from collections.abc import AsyncIterator

from redis.asyncio import Redis

from src.settings import settings


async def get_redis_client() -> AsyncIterator[Redis]:
    redis = Redis.from_url(
        settings.REDIS_URL, decode_responses=True, health_check_interval=30,
    )
    yield redis
    await redis.aclose()

