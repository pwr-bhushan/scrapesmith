"""Async SQLAlchemy engine + session factory."""
from __future__ import annotations

from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

# ponytail: NullPool — no cross-event-loop connection reuse (fixes test loops; DB isn't the
# bottleneck here, render is). Switch to a real pool if DB throughput ever matters.
engine = create_async_engine(settings.database_url, future=True, poolclass=NullPool)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session():
    """FastAPI dependency: an async session per request."""
    async with SessionLocal() as session:
        yield session
