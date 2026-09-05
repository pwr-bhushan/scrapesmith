"""OllamaProvider — default local heal provider.

Calls Ollama REST API at http://localhost:11434 (or OLLAMA_HOST env var).
Model is configurable via constructor argument (default: qwen2.5-coder:7b).

ponytail: httpx POST + JSON parse; validate_proposal handles output cleaning.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Mapping, Sequence

import httpx

from spike.heal.prompt import build_prompt
from spike.heal.provider import Failure, FieldSpec, HealProvider, Proposal, validate_proposal

logger = logging.getLogger(__name__)


class OllamaProvider(HealProvider):
    """Heal provider backed by a local Ollama model."""

    DEFAULT_MODEL = "qwen2.5-coder:7b"
    DEFAULT_HOST = "http://localhost:11434"
    # Greedy decoding by default. Without it Ollama samples at the model default (~0.8) and
    # four identical bench runs scored 91.7 / 91.7 / 97.9 / 97.9 — a 6.3pp spread, wider than
    # any effect heal memory is expected to produce, which makes a k-sweep unattributable.
    # `seed` still matters at temperature 0: it pins tie-breaking between equal-probability tokens.
    DEFAULT_SEED = 1234
    # Measured 2026-09-05: the corpus's largest k=0 prompt is 1244 tokens against Ollama's
    # 4096 default, so B1's numbers were never truncated. Pinned anyway so few-shot examples
    # have headroom and an Ollama upgrade cannot move the window silently.
    DEFAULT_NUM_CTX = 8192

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        host: str = DEFAULT_HOST,
        temperature: float = 0.0,
        seed: int = DEFAULT_SEED,
        num_ctx: int = DEFAULT_NUM_CTX,
    ) -> None:
        self.model = model
        self.host = os.environ.get("OLLAMA_HOST", host)
        self.temperature = temperature
        self.seed = seed
        self.num_ctx = num_ctx

    @property
    def name(self) -> str:
        return f"ollama/{self.model}"

    def propose(
        self,
        cleaned_html: str,
        fields: List[FieldSpec],
        failures: List[Failure],
        examples: Sequence[Mapping[str, Any]] = (),
    ) -> Dict[str, Proposal]:
        prompt = build_prompt(cleaned_html, fields, failures, examples=examples)
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": self.temperature,
                "seed": self.seed,
                "num_ctx": self.num_ctx,
            },
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
