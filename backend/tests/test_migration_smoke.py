"""Phase 0.5 smoke: `alembic upgrade head` creates all 6 tables.

Sync test: alembic's async env.py runs its own asyncio.run(), so it must not be nested inside
pytest-asyncio's loop. Gated on a reachable Postgres (skips cleanly otherwise).
"""
import asyncio
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.config import Config
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import command
from app.config import settings
from tests._svc import url_reachable

pytestmark = pytest.mark.skipif(
    not url_reachable(settings.database_url, 5432), reason="postgres not reachable"
)

BACKEND = Path(__file__).resolve().parent.parent
EXPECTED = {"domain", "config_version", "upload_batch", "upload_file", "parse_result", "job"}


async def _public_tables() -> set:
    engine = create_async_engine(settings.database_url)
    try:
        async with engine.connect() as conn:
            rows = await conn.execute(
                sa.text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            )
            return {r[0] for r in rows}
    finally:
        await engine.dispose()


def test_upgrade_head_creates_tables():
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    command.upgrade(cfg, "head")  # idempotent no-op if already at head

    tables = asyncio.run(_public_tables())
    assert EXPECTED.issubset(tables), EXPECTED - tables
