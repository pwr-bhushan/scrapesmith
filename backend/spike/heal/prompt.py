"""Prompt builder shared by OllamaProvider and CloudProvider.

ponytail: plain f-string template; no Jinja dependency.
"""
from __future__ import annotations

from typing import List

from spike.heal.provider import Failure, FieldSpec


def build_prompt(
    cleaned_html: str,
    fields: List[FieldSpec],
    failures: List[Failure],
) -> str:
    """Build the LLM prompt for selector healing.

    Args:
        cleaned_html: Output of ``clean_html()``.
        fields: All field specs (for context).
        failures: Fields that need new selectors.

    Returns:
        Prompt string ready for the LLM.
    """
    failure_names = {f.field_name for f in failures}
    failed_specs = [f for f in fields if f.name in failure_names]

    field_lines = "\n".join(
        f"  - {f.name} (type={f.field_type}, old_selector={f.old_selector!r})"
        for f in failed_specs
    )

    return (
        "You are a CSS/XPath selector repair agent.\n\n"
        "The following fields could not be extracted from the current HTML "
        "because their selectors no longer match after a site redesign.\n\n"
        f"Fields to heal:\n{field_lines}\n\n"
        "HTML (cleaned):\n"
        "```\n"
        f"{cleaned_html}\n"
        "```\n\n"
        "Respond with a JSON object mapping each field name to a new selector.\n"
        "Every selector MUST be prefixed with either 'css=' or 'xpath='.\n"
        "Example:\n"
        '{"price": "css=.a-price-whole", "title": "css=.pdp-product-name"}\n'
    )
