"""CloudProvider — Anthropic Claude heal provider (opt-in).

Cloud model ID is configurable via:
  1. Constructor arg ``model`` (highest priority)
  2. Environment variable ``SCRAPESMITH_CLOUD_MODEL``
  3. Default: ``claude-haiku-4-5``

API key is read from ``ANTHROPIC_API_KEY`` env var (standard Anthropic SDK behaviour).

ponytail: anthropic SDK messages.create; validate_proposal handles output cleaning.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Mapping, Sequence

from spike.heal.prompt import build_prompt
from spike.heal.provider import Failure, FieldSpec, HealProvider, Proposal, validate_proposal

logger = logging.getLogger(__name__)

DEFAULT_CLOUD_MODEL = "claude-haiku-4-5"


class CloudProvider(HealProvider):
    """Heal provider backed by Anthropic Claude (cloud)."""

    def __init__(self, model: str | None = None) -> None:
        self.model = (
            model
            or os.environ.get("SCRAPESMITH_CLOUD_MODEL")
            or DEFAULT_CLOUD_MODEL
        )

    @property
    def name(self) -> str:
        return f"cloud/{self.model}"

    def propose(
        self,
        cleaned_html: str,
        fields: List[FieldSpec],
        failures: List[Failure],
        examples: Sequence[Mapping[str, Any]] = (),
    ) -> Dict[str, Proposal]:
        import anthropic

        prompt = build_prompt(cleaned_html, fields, failures, examples=examples)
        client = anthropic.Anthropic()
        try:
            message = client.messages.create(
                model=self.model,
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
            )
            raw_text = message.content[0].text
            raw: Dict[str, str] = json.loads(raw_text)
        except Exception as exc:
            logger.error("CloudProvider.propose failed: %s", exc)
            return {}
        return validate_proposal(raw, failures)
