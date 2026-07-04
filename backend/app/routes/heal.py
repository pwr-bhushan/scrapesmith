"""Heal routes (§10): POST /heal/propose (cluster + propose + post-check), POST /heal/accept."""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.aggregate import field_rates
from app.batch_parse import gather_results
from app.db import get_session
from app.heal import cluster_failures, failing_fields, post_check, select_provider
from app.models import Domain, UploadBatch
from app.storage import create_config_version, effective_config_version

router = APIRouter()


class HealRequest(BaseModel):
    batch_id: uuid.UUID


class AcceptRequest(BaseModel):
    batch_id: uuid.UUID
    accepted: dict  # {field_name: selector}


def _fieldspecs_failures(fields, failing, rep):
    """Build spike FieldSpec + Failure lists for the provider from config + the rep's statuses."""
    from spike.heal.provider import Failure, FieldSpec

    specs = [
        FieldSpec(
            name=f["name"],
            field_type=f.get("type") or "text",
            old_selector=f.get("selector", ""),
        )
        for f in fields
    ]
    failures = [
        Failure(
            field_name=name,
            dq_status=rep["field_status"].get(name, "empty"),
            extracted_value=(
                rep["data"].get(name) if isinstance(rep["data"].get(name), str) else None
            ),
        )
        for name in failing
    ]
    return specs, failures


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
    rates = field_rates(results, cv.fields)
    failing = failing_fields(rates)
    if not failing:
        return {"triggered": False, "field_rates": rates}

    clusters = cluster_failures(results, failing)
    fields_by_name = {f["name"]: f for f in cv.fields}
    provider = select_provider()

    cluster_out = []
    for cl in clusters:
        rep = cl["representative"]
        entry = {"hash": cl["hash"], "size": cl["size"], "representative": rep["file"]}
        if provider is None:
            entry["proposals"] = {}
            entry["model"] = "unavailable"
        else:
            from spike.cleaner import clean_html

            cleaned = clean_html(Path(rep["path"]).read_text(encoding="utf-8", errors="replace"))
            specs, failures = _fieldspecs_failures(cv.fields, failing, rep)
            proposed = provider.propose(cleaned, specs, failures)
            selectors = {name: pr.selector for name, pr in proposed.items()}
            cluster_paths = [f["path"] for f in cl["files"][1:]]
            checked = await post_check(
                selectors, rep["path"], cluster_paths, fields_by_name, render_js
            )
            # attach the anchor value for the value-first diff (5.7)
            for name, c in checked.items():
                c["anchor"] = (fields_by_name.get(name, {}).get("anchor") or {}).get("value")
            entry["proposals"] = checked
            entry["model"] = provider.name
        cluster_out.append(entry)

    return {"triggered": True, "failing": failing, "field_rates": rates, "clusters": cluster_out}


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
