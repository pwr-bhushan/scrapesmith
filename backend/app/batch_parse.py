"""Batch parse: run a config over every file in a batch, storing results + job progress (§7)."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ConfigVersion, Domain, Job, ParseResult, UploadBatch
from app.parser import parse_config
from app.storage import _index_of, list_batch_files


async def run_batch(
    session: AsyncSession, job_id: uuid.UUID, batch_id: uuid.UUID, cv: ConfigVersion
):
    """Parse every file; store a parse_result each; update job.progress incrementally."""
    batch = await session.get(UploadBatch, batch_id)
    domain = await session.get(Domain, batch.domain_id)
    render_js = bool(domain and domain.render_js)
    files = await list_batch_files(session, batch_id)

    job = await session.get(Job, job_id)
    job.state = "running"
    total = len(files)
    job.progress = {"done": 0, "total": total, "phase": "parsing"}
    await session.commit()

    for done, uf in enumerate(files, start=1):
        result = await parse_config(uf.raw_html_path, cv.fields, render_js)
        session.add(
            ParseResult(
                file_id=uf.id,
                config_version_id=cv.id,
                data=result["data"],
                flags=result["flags"],
                field_status=result["field_status"],
            )
        )
        job.progress = {"done": done, "total": total, "phase": "parsing"}
        await session.commit()

    job.state = "done"
    await session.commit()


async def gather_results(session: AsyncSession, batch_id: uuid.UUID, cv_id: uuid.UUID) -> list:
    """Reconstruct per-file results (latest parse_result per file) for aggregation/export."""
    files = await list_batch_files(session, batch_id)
    file_by_id = {f.id: f for f in files}
    rows = (
        await session.execute(
            select(ParseResult)
            .where(ParseResult.config_version_id == cv_id)
            .order_by(ParseResult.created_at)
        )
    ).scalars().all()

    # keep the latest parse_result per file
    latest: dict = {}
    for r in rows:
        if r.file_id in file_by_id:
            latest[r.file_id] = r

    out = []
    for fid, r in sorted(latest.items(), key=lambda kv: _index_of(file_by_id[kv[0]].raw_html_path)):
        uf = file_by_id[fid]
        out.append(
            {
                "file": uf.filename,
                "path": uf.raw_html_path,
                "dom_skeleton_hash": uf.dom_skeleton_hash,
                "data": r.data or {},
                "field_status": r.field_status or {},
                "flags": r.flags or {},
            }
        )
    return out
