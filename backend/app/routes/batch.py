"""GET /batch/{id} and GET /batch/{id}/file/{index}/render."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Domain, UploadBatch
from app.render import render_snapshot
from app.storage import _index_of, file_at_index, list_batch_files

router = APIRouter()


@router.get("/batch/{batch_id}")
async def get_batch(batch_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    batch = await session.get(UploadBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="batch not found")
    files = await list_batch_files(session, batch_id)
    return {
        "batch_id": str(batch.id),
        "domain_id": str(batch.domain_id),
        "status": batch.status,
        "file_count": batch.file_count,
        "files": [
            {"index": _index_of(f.raw_html_path), "filename": f.filename,
             "dom_skeleton_hash": f.dom_skeleton_hash}
            for f in files
        ],
    }


@router.get("/batch/{batch_id}/file/{index}/render", response_class=HTMLResponse)
async def render_file_snapshot(
    batch_id: uuid.UUID, index: int, session: AsyncSession = Depends(get_session)
):
    uf = await file_at_index(session, batch_id, index)
    if uf is None:
        raise HTTPException(status_code=404, detail="file not found")
    batch = await session.get(UploadBatch, batch_id)
    domain = await session.get(Domain, batch.domain_id)  # render_js lives on the domain
    html = await render_snapshot(uf.raw_html_path, render_js=bool(domain and domain.render_js))
    return HTMLResponse(content=html)
