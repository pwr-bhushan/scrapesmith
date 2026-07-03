"""FastAPI app. Phase 0.5: /health only."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import batch, config, infer, parse, pick, upload

app = FastAPI(title="scrapesmith", version="0.1.0")

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
