"""arq worker. Phase 0.5: a single no-op task to prove the queue round-trips."""
from __future__ import annotations

from arq.connections import RedisSettings

from app.config import settings


async def noop(ctx: dict) -> str:
    """Smoke task: does nothing, returns a sentinel the enqueuer can assert on."""
    return "ok"


class WorkerSettings:
    functions = [noop]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
