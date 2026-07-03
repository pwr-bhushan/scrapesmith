"""POST /upload — ingest html/.gz/.zip, persist, fingerprint."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.storage import create_batch_with_files, get_or_create_domain
from app.upload import UploadError, extract_html_files

router = APIRouter()


@router.post("/upload")
async def upload(
    file: UploadFile = File(...),
    host: str = Form(...),
    page_type: str = Form(...),
    render_js: bool = Form(True),
    notes: str = Form(""),
    session: AsyncSession = Depends(get_session),
):
    data = await file.read()
    try:
        files = extract_html_files(file.filename or "upload.html", data)
    except UploadError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    domain = await get_or_create_domain(session, host, page_type, render_js)
    batch = await create_batch_with_files(session, domain, files)
    await session.commit()

    return {
        "batch_id": str(batch.id),
        "domain_id": str(domain.id),
        "file_count": len(files),
        "files": [{"index": i, "filename": n} for i, (n, _) in enumerate(files)],
    }
