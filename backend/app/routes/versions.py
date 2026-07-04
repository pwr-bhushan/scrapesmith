"""Version routes (§11): list versions, diff two versions, pin a batch to a version."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import UploadBatch
from app.storage import config_version_at, list_config_versions
from app.versioning import diff_fields

router = APIRouter()


@router.get("/domains/{domain_id}/versions")
async def versions(domain_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    cvs = await list_config_versions(session, domain_id)
    return {
        "versions": [
            {
                "id": str(cv.id),
                "version": cv.version,
                "created_by": cv.created_by,
                "parent_version": cv.parent_version,
                "field_count": len(cv.fields or []),
            }
            for cv in cvs
        ]
    }


@router.get("/domains/{domain_id}/diff")
async def diff(
    domain_id: uuid.UUID, a: int, b: int, session: AsyncSession = Depends(get_session)
):
    cv_a = await config_version_at(session, domain_id, a)
    cv_b = await config_version_at(session, domain_id, b)
    if cv_a is None or cv_b is None:
        raise HTTPException(status_code=404, detail="version not found")
    return {"a": a, "b": b, "diff": diff_fields(cv_a.fields or [], cv_b.fields or [])}


class PinRequest(BaseModel):
    version: int


@router.post("/batch/{batch_id}/pin")
async def pin(
    batch_id: uuid.UUID, req: PinRequest, session: AsyncSession = Depends(get_session)
):
    batch = await session.get(UploadBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="batch not found")
    cv = await config_version_at(session, batch.domain_id, req.version)
    if cv is None:
        raise HTTPException(status_code=404, detail="version not found")
    batch.config_version_id = cv.id
    await session.commit()
    return {"batch_id": str(batch_id), "pinned_version": cv.version}
