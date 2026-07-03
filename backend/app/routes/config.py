"""POST/GET /batch/{id}/config — save & read config v1 for a batch's domain."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import UploadBatch
from app.storage import create_config_version, latest_config_version

router = APIRouter()


class ConfigField(BaseModel):
    name: str
    selector: str
    scope: str = "single"  # "single" | "list"
    list_parent_selector: Optional[str] = None
    type: Optional[str] = None  # Phase 3 inference
    dq: Optional[dict] = None  # Phase 3 preset default; evaluated by the Phase 4 DQ engine
    anchor: Optional[dict] = None  # Phase 4 §10: {value, fingerprint} captured at Confirm


class SaveConfigRequest(BaseModel):
    fields: list[ConfigField]


@router.post("/batch/{batch_id}/config")
async def save_config(
    batch_id: uuid.UUID, req: SaveConfigRequest, session: AsyncSession = Depends(get_session)
):
    batch = await session.get(UploadBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="batch not found")
    if not req.fields:
        raise HTTPException(status_code=400, detail="config needs at least one field")

    cv = await create_config_version(
        session, batch.domain_id, [f.model_dump() for f in req.fields]
    )
    batch.config_version_id = cv.id
    await session.commit()
    return {"config_version_id": str(cv.id), "version": cv.version, "field_count": len(req.fields)}


@router.get("/batch/{batch_id}/config")
async def get_config(batch_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    batch = await session.get(UploadBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="batch not found")
    cv = await latest_config_version(session, batch.domain_id)
    if cv is None:
        return {"version": None, "fields": []}
    return {"config_version_id": str(cv.id), "version": cv.version, "fields": cv.fields}
