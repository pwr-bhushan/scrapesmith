"""OllamaProvider — default local heal provider.

Calls Ollama REST API at http://localhost:11434 (or OLLAMA_HOST env var).
Model is configurable via constructor argument (default: qwen2.5-coder:7b).

ponytail: httpx POST + JSON parse; validate_proposal handles output cleaning.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Dict, List

import httpx

from spike.heal.prompt import build_prompt
from spike.heal.provider import Failure, FieldSpec, HealProvider, Proposal, validate_proposal

logger = logging.getLogger(__name__)


class OllamaProvider(HealProvider):
    """Heal provider backed by a local Ollama model."""

    DEFAULT_MODEL = "qwen2.5-coder:7b"
    DEFAULT_HOST = "http://localhost:11434"

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        host: str = DEFAULT_HOST,
    ) -> None:
        self.model = model
        self.host = os.environ.get("OLLAMA_HOST", host)

    @property
    def name(self) -> str:
        return f"ollama/{self.model}"

    def propose(
        self,
        cleaned_html: str,
        fields: List[FieldSpec],
        failures: List[Failure],
    ) -> Dict[str, Proposal]:
        prompt = build_prompt(cleaned_html, fields, failures)
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }
        try:
            resp = httpx.post(
                f"{self.host}/api/generate",
                json=payload,
                timeout=60.0,
            )
            resp.raise_for_status()
            raw_text = resp.json().get("response", "{}")
            raw: Dict[str, str] = json.loads(raw_text)
        except Exception as exc:
            logger.error("OllamaProvider.propose failed: %s", exc)
            return {}
        return validate_proposal(raw, failures)
