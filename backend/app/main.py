"""FastAPI app. Phase 0.5: /health only."""
from __future__ import annotations

import contextlib
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import check_settings, safe_database_url, settings
from app.routes import batch, config, heal, infer, jobs, parse, pick, upload, versions

logger = logging.getLogger(__name__)


@contextlib.asynccontextmanager
async def lifespan(_: FastAPI):
    # Refuse to boot on dev defaults outside SCRAPESMITH_ENV=local, and say what connected.
    check_settings()
    logger.info(
        "scrapesmith starting: env=%s db=%s", settings.env, safe_database_url(settings.database_url)
    )
    yield


app = FastAPI(title="scrapesmith", version="0.1.0", lifespan=lifespan)

# Dev-open CORS so the Next.js hello page can call /health. Tighten in a later phase.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


app.include_router(upload.router)
app.include_router(batch.router)
app.include_router(pick.router)
app.include_router(config.router)
app.include_router(infer.router)
app.include_router(parse.router)
app.include_router(jobs.router)
app.include_router(heal.router)
app.include_router(versions.router)
