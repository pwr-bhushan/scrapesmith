"""arq redis pool accessor for enqueuing jobs from the API side."""
from __future__ import annotations

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.config import settings


async def get_pool() -> ArqRedis:
    return await create_pool(RedisSettings.from_dsn(settings.redis_url))
