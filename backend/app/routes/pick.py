"""POST /pick/validate — descriptor -> generated, validated selector (§8.1/§8.2)."""
from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Domain, UploadBatch
from app.pick import resolve_many
from app.selector import list_candidates, single_candidates
from app.storage import file_at_index

router = APIRouter()


class ValidateRequest(BaseModel):
    batch_id: uuid.UUID
    index: int
    descriptor: dict[str, Any]
    scope: str = "single"  # "single" | "list"
    list_parent_selector: Optional[str] = None


@router.post("/pick/validate")
async def validate_pick(req: ValidateRequest, session: AsyncSession = Depends(get_session)):
    uf = await file_at_index(session, req.batch_id, req.index)
    if uf is None:
        raise HTTPException(status_code=404, detail="file not found")
    batch = await session.get(UploadBatch, req.batch_id)
    domain = await session.get(Domain, batch.domain_id)
    render_js = bool(domain and domain.render_js)

    if req.scope == "list":
        if not req.list_parent_selector:
            raise HTTPException(status_code=400, detail="list scope needs list_parent_selector")
        candidates = list_candidates(req.descriptor, req.list_parent_selector)
        wants = lambda c: c >= 2  # noqa: E731
    else:
        candidates = single_candidates(req.descriptor)
        wants = lambda c: c == 1  # noqa: E731

    if not candidates:
        raise HTTPException(status_code=422, detail="no candidate selectors from descriptor")

    results = await resolve_many(uf.raw_html_path, candidates, render_js)
    for r in results:
        if wants(r["count"]):
            return {
                "resolves": True,
                "selector": f"css={r['selector']}",
                "count": r["count"],
                "values": r["values"],
                "scope": req.scope,
                "list_parent_selector": req.list_parent_selector,
            }
    # nothing uniquely resolved — return the best attempt for surfacing
    best = (
        max(results, key=lambda r: r["count"])
        if results
        else {"selector": "", "count": 0, "values": []}
    )
    return {
        "resolves": False,
        "selector": f"css={best['selector']}" if best["selector"] else None,
        "count": best["count"],
        "values": best["values"],
        "scope": req.scope,
        "list_parent_selector": req.list_parent_selector,
    }
