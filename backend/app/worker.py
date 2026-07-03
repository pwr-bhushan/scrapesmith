"""arq worker: no-op smoke task (Phase 0.5) + batch_parse (Phase 5)."""
from __future__ import annotations

import uuid

from arq.connections import RedisSettings

from app.config import settings
from app.db import SessionLocal
from app.models import ConfigVersion, Job


async def noop(ctx: dict) -> str:
    """Smoke task: does nothing, returns a sentinel the enqueuer can assert on."""
    return "ok"


async def batch_parse(ctx: dict, job_id: str, batch_id: str, cv_id: str) -> str:
    """Parse a whole batch in the background (§7)."""
    from app.batch_parse import run_batch  # local import to avoid Playwright at module load

    async with SessionLocal() as session:
        cv = await session.get(ConfigVersion, uuid.UUID(cv_id))
        try:
            await run_batch(session, uuid.UUID(job_id), uuid.UUID(batch_id), cv)
        except Exception as exc:  # mark the job failed rather than dying silently
            job = await session.get(Job, uuid.UUID(job_id))
            if job:
                job.state = "failed"
                job.error = str(exc)[:1000]
                await session.commit()
            raise
    return "done"


class WorkerSettings:
    functions = [noop, batch_parse]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
