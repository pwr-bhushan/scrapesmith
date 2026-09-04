"""POST /infer — click element context -> field type + confidence (§8). GET /presets."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.infer import classify_with_llm, infer_type
from app.presets import PRESET_TYPES

router = APIRouter()


class InferRequest(BaseModel):
    text: str = ""
    itemprop: str = ""
    data: dict | None = None
    label: str = ""
    use_llm: bool = False


@router.get("/presets")
async def presets():
    return {"types": PRESET_TYPES}


@router.post("/infer")
async def infer(req: InferRequest):
    result = infer_type(text=req.text, itemprop=req.itemprop, data=req.data, label=req.label)
    if result["type"] is None and req.use_llm:
        result = classify_with_llm(req.text, req.label)
    return result
