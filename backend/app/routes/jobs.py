"""Batch parse job routes: enqueue, status, SSE progress, results, export (§7/§9/§579)."""
from __future__ import annotations

import asyncio
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.aggregate import field_rates, flagged_ratios
from app.batch_parse import gather_results
from app.db import SessionLocal, get_session
from app.export import csv_rows, json_tree
from app.models import Job, UploadBatch
from app.queue import get_pool
from app.storage import latest_config_version

router = APIRouter()


class BatchRequest(BaseModel):
    batch_id: uuid.UUID


@router.post("/parse/batch")
async def parse_batch(req: BatchRequest, session: AsyncSession = Depends(get_session)):
    batch = await session.get(UploadBatch, req.batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="batch not found")
    cv = await latest_config_version(session, batch.domain_id)
    if cv is None:
        raise HTTPException(status_code=400, detail="no config saved for this domain")

    job = Job(
        batch_id=req.batch_id,
        kind="batch_parse",
        state="queued",
        progress={"done": 0, "total": batch.file_count or 0, "phase": "queued"},
    )
    session.add(job)
    await session.commit()

    pool = await get_pool()
    await pool.enqueue_job("batch_parse", str(job.id), str(req.batch_id), str(cv.id))
    await pool.aclose()
    return {"job_id": str(job.id), "config_version": cv.version}


@router.get("/jobs/{job_id}")
async def job_status(job_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    job = await session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return {"job_id": str(job.id), "state": job.state, "progress": job.progress, "error": job.error}


@router.get("/jobs/{job_id}/stream")
async def job_stream(job_id: uuid.UUID):
    async def events():
        while True:
            async with SessionLocal() as s:
                job = await s.get(Job, job_id)
            if job is None:
                yield f"data: {json.dumps({'error': 'not found'})}\n\n"
                return
            yield f"data: {json.dumps({'state': job.state, 'progress': job.progress})}\n\n"
            if job.state in ("done", "failed"):
                return
            await asyncio.sleep(0.5)

    return StreamingResponse(events(), media_type="text/event-stream")


async def _results_for_batch(session: AsyncSession, batch_id: uuid.UUID):
    batch = await session.get(UploadBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="batch not found")
    cv = await latest_config_version(session, batch.domain_id)
    if cv is None:
        raise HTTPException(status_code=400, detail="no config for this domain")
    return cv, await gather_results(session, batch_id, cv.id)


@router.get("/batch/{batch_id}/results")
async def batch_results(batch_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    cv, results = await _results_for_batch(session, batch_id)
    return {
        "config_version": cv.version,
        "file_count": len(results),
        "field_rates": field_rates(results, cv.fields),
        "flagged": flagged_ratios(results, cv.fields),
        "rows": results,
    }


@router.get("/batch/{batch_id}/export.csv", response_class=PlainTextResponse)
async def export_csv(batch_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    cv, results = await _results_for_batch(session, batch_id)
    return PlainTextResponse(csv_rows(results, cv.fields), media_type="text/csv")


@router.get("/batch/{batch_id}/export.json")
async def export_json(batch_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    _, results = await _results_for_batch(session, batch_id)
    return json_tree(results)
