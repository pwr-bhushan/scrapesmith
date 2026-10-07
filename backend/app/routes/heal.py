"""Heal routes (§10): POST /heal/propose (runs the heal graph), POST /heal/accept."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.batch_parse import gather_results
from app.db import get_session
from app.heal import select_provider
from app.heal_graph import DEFAULT_MAX_ATTEMPTS, run_heal
from app.models import Domain, UploadBatch
from app.storage import create_config_version, effective_config_version

router = APIRouter()


class HealRequest(BaseModel):
    batch_id: uuid.UUID
    # attempts per cluster; each one is a model call plus a Playwright gate run
    max_attempts: int = Field(DEFAULT_MAX_ATTEMPTS, ge=1, le=5)


class AcceptRequest(BaseModel):
    batch_id: uuid.UUID
    accepted: dict  # {field_name: selector}
    # the config_version the proposal was made against; a mismatch means the config moved on
    # (another accept, a pin) and these selectors would overwrite it
    expected_version: int | None = None


@router.post("/heal/propose")
async def heal_propose(req: HealRequest, session: AsyncSession = Depends(get_session)):
    batch = await session.get(UploadBatch, req.batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="batch not found")
    cv = await effective_config_version(session, batch)
    if cv is None:
        raise HTTPException(status_code=400, detail="no config for this domain")
    domain = await session.get(Domain, batch.domain_id)
    render_js = bool(domain and domain.render_js)

    results = await gather_results(session, req.batch_id, cv.id)
    out = await run_heal(results, cv.fields, select_provider(), render_js, req.max_attempts)
    out["config_version"] = cv.version

    # attach the anchor value for the value-first diff (5.7)
    fields_by_name = {f["name"]: f for f in cv.fields}
    for cl in out.get("clusters", []):
        for name, c in cl["proposals"].items():
            c["anchor"] = (fields_by_name.get(name, {}).get("anchor") or {}).get("value")
    return out


@router.post("/heal/accept")
async def heal_accept(req: AcceptRequest, session: AsyncSession = Depends(get_session)):
    batch = await session.get(UploadBatch, req.batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="batch not found")
    cv = await effective_config_version(session, batch)
    if cv is None:
        raise HTTPException(status_code=400, detail="no config for this domain")
    if not req.accepted:
        raise HTTPException(status_code=400, detail="no accepted selectors")
    if req.expected_version is not None and req.expected_version != cv.version:
        raise HTTPException(
            status_code=409,
            detail=f"config is now v{cv.version}, proposal was for v{req.expected_version}; "
                   "propose again",
        )

    new_fields = []
    for f in cv.fields:
        nf = dict(f)
        if f["name"] in req.accepted:
            nf["selector"] = req.accepted[f["name"]]
        new_fields.append(nf)

    new_cv = await create_config_version(
        session, batch.domain_id, new_fields, created_by="llm-heal"
    )
    batch.config_version_id = new_cv.id
    await session.commit()
    return {
        "config_version_id": str(new_cv.id),
        "version": new_cv.version,
        "healed": list(req.accepted),
    }
