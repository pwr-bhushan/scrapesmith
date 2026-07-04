"""POST /parse/canary — run the saved config on one file, store result, return panel (§5.5)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.dq import normalize
from app.models import Domain, ParseResult, UploadBatch
from app.parser import parse_config
from app.storage import effective_config_version, file_at_index

router = APIRouter()


class CanaryRequest(BaseModel):
    batch_id: uuid.UUID
    index: int


def _anchor_ok(field: dict, parsed) -> bool | None:
    anchor = field.get("anchor")
    if not anchor or "value" not in anchor:
        return None
    kind = "number" if (field.get("dq") or {}).get("parses_as") == "number" else "text"
    got = parsed[0] if isinstance(parsed, list) and parsed else parsed
    return normalize(str(got), kind) == normalize(str(anchor["value"]), kind)


@router.post("/parse/canary")
async def canary(req: CanaryRequest, session: AsyncSession = Depends(get_session)):
    uf = await file_at_index(session, req.batch_id, req.index)
    if uf is None:
        raise HTTPException(status_code=404, detail="file not found")
    batch = await session.get(UploadBatch, req.batch_id)
    cv = await effective_config_version(session, batch)
    if cv is None:
        raise HTTPException(status_code=400, detail="no config saved for this domain")
    domain = await session.get(Domain, batch.domain_id)

    result = await parse_config(uf.raw_html_path, cv.fields, bool(domain and domain.render_js))

    anchors = {f["name"]: _anchor_ok(f, result["data"].get(f["name"])) for f in cv.fields}

    session.add(
        ParseResult(
            file_id=uf.id,
            config_version_id=cv.id,
            data=result["data"],
            flags=result["flags"],
            field_status=result["field_status"],
        )
    )
    await session.commit()

    return {
        "file_index": req.index,
        "filename": uf.filename,
        "config_version": cv.version,
        "data": result["data"],
        "field_status": result["field_status"],
        "flags": result["flags"],
        "anchor_ok": anchors,
    }
