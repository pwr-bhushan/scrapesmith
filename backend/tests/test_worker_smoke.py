"""Phase 0.5 smoke: enqueue a no-op arq job and let a burst worker drain it.

Gated on a reachable Redis (skips cleanly otherwise).
"""
import pytest
from arq import create_pool
from arq.connections import RedisSettings
from arq.worker import Worker

from app.config import settings
from app.worker import noop
from tests._svc import url_reachable

pytestmark = pytest.mark.skipif(
    not url_reachable(settings.redis_url, 6379), reason="redis not reachable"
)


async def test_noop_job_roundtrips():
    rs = RedisSettings.from_dsn(settings.redis_url)
    pool = await create_pool(rs)
    try:
        job = await pool.enqueue_job("noop")
        worker = Worker(functions=[noop], redis_settings=rs, burst=True, poll_delay=0.1)
        await worker.main()
        assert await job.result(timeout=5) == "ok"
    finally:
        await pool.aclose()
