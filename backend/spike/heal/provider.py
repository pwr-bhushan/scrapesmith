"""HealProvider ABC and supporting dataclasses.

Contract:
  propose(cleaned_html: str, fields: list[FieldSpec], failures: list[Failure])
      -> dict[str, Proposal]

  Key rules enforced by validate_proposal():
    - Every field name in ``failures`` must appear as a key in the response dict.
    - Every ``Proposal.selector`` must be prefixed with ``"css="`` or ``"xpath="``.
    - Proposals with a missing key are excluded (not a hard error) — callers
      must handle missing fields.
    - Proposals with a non-prefixed selector are REJECTED and excluded from the
      validated output; a warning is logged.

ponytail: minimal dataclasses + ABC; validate_proposal is a short filter loop.
"""
from __future__ import annotations

import abc
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

VALID_PREFIXES = ("css=", "xpath=")


@dataclass
class FieldSpec:
    """Specification for a field that needs healing."""
    name: str
    field_type: str  # "currency" | "number" | "text"
    old_selector: str
    dq_rule: Optional[object] = None  # DQRule — loosely typed to avoid circular import


@dataclass
class Failure:
    """A field that failed DQ or resolution."""
    field_name: str
    dq_status: str  # DQStatus value
    extracted_value: Optional[str] = None


@dataclass
class Proposal:
    """A healed selector proposed by a HealProvider."""
    selector: str
    confidence: float = 1.0


class HealProvider(abc.ABC):
    """Abstract base class for heal providers.

    Concrete implementations: OllamaProvider, CloudProvider, FakeProvider.
    """

    @abc.abstractmethod
    def propose(
        self,
        cleaned_html: str,
        fields: List[FieldSpec],
        failures: List[Failure],
    ) -> Dict[str, Proposal]:
        """Propose healed selectors for the given failures.

        Args:
            cleaned_html: Cleaned HTML text from ``clean_html()``.
            fields: Full list of ``FieldSpec`` objects for context.
            failures: Fields that failed DQ or resolution.

        Returns:
            Dict mapping field name → ``Proposal``.
            Only fields present in ``failures`` need to be included.
        """


def validate_proposal(
    raw: Dict[str, str],
    failures: List[Failure],
) -> Dict[str, Proposal]:
    """Validate and normalise raw provider output.

    Args:
        raw: Dict mapping field name → raw selector string (provider output).
        failures: List of ``Failure`` objects for the fields being healed.

    Returns:
        Dict of validated ``Proposal`` objects.
        Fields with missing keys are excluded.
        Fields with non-prefixed selectors are excluded with a warning.
    """
    result: Dict[str, Proposal] = {}
    for failure in failures:
        name = failure.field_name
        if name not in raw:
            # Missing key — silently exclude
            continue
        selector = raw[name]
        if not selector.startswith(VALID_PREFIXES):
            logger.warning(
                "Excluding field %r: selector %r lacks css=/xpath= prefix", name, selector
            )
            continue
        result[name] = Proposal(selector=selector)
    return result
