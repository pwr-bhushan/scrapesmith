"""Inference cascade (design §8): structured data → text regex → label proximity → opt-in LLM."""
from __future__ import annotations

import os
import re
from typing import Optional

from app.presets import FIELD_PRESETS, default_dq

# itemprop name -> field type (tier 1)
_ITEMPROP_MAP = {
    name: ftype for ftype, p in FIELD_PRESETS.items() for name in p["itemprop"]
}


def _result(field_type: Optional[str], confidence: float, source: str) -> dict:
    return {
        "type": field_type,
        "confidence": confidence,
        "source": source,
        "dq": default_dq(field_type) if field_type else {"required": False},
    }


def infer_type(
    text: str = "",
    itemprop: str = "",
    data: Optional[dict] = None,
    label: str = "",
) -> dict:
    """Deterministic tiers 1–3. Returns {type, confidence, source, dq}."""
    data = data or {}
    text = (text or "").strip()

    # tier 1: structured data (itemprop, then data-* key names)
    if itemprop and itemprop in _ITEMPROP_MAP:
        return _result(_ITEMPROP_MAP[itemprop], 0.95, "structured")
    for key in data:
        for ftype, preset in FIELD_PRESETS.items():
            if any(syn in key.lower() for syn in preset["synonyms"]):
                return _result(ftype, 0.9, "structured")

    # tier 2: text regex
    if text:
        for ftype, preset in FIELD_PRESETS.items():
            rx = preset["regex"]
            if rx and re.search(rx, text):
                return _result(ftype, 0.85, "regex")

    # tier 3: label proximity via synonyms
    if label:
        low = label.lower()
        for ftype, preset in FIELD_PRESETS.items():
            if any(syn in low for syn in preset["synonyms"]):
                return _result(ftype, 0.70, "label")

    return _result(None, 0.0, "none")


def llm_available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def classify_with_llm(text: str, context: str = "") -> dict:
    """Tier 4 — opt-in. Honest 'unavailable' when no model is wired (no ANTHROPIC_API_KEY)."""
    if not llm_available():
        return _result(None, 0.0, "llm_unavailable")
    try:
        import anthropic

        model = os.environ.get("SCRAPESMITH_CLOUD_MODEL", "claude-haiku-4-5")
        types = ", ".join(FIELD_PRESETS.keys())
        prompt = (
            f"Classify this web element into exactly one type from [{types}] or 'custom'. "
            f"Answer with only the type word.\nElement text: {text!r}\nContext: {context[:200]!r}"
        )
        client = anthropic.Anthropic()
        msg = client.messages.create(
            model=model, max_tokens=8, messages=[{"role": "user", "content": prompt}]
        )
        answer = msg.content[0].text.strip().lower()
        if answer in FIELD_PRESETS:
            return _result(answer, 0.60, "llm")
        return _result(None, 0.0, "llm")
    except Exception:
        return _result(None, 0.0, "llm_unavailable")
