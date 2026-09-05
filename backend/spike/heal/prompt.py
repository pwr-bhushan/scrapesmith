"""Prompt builder shared by OllamaProvider and CloudProvider.

ponytail: plain f-string template; no Jinja dependency.
"""
from __future__ import annotations

from typing import Any, List, Mapping, Sequence

from spike.heal.provider import Failure, FieldSpec


def _render_examples(examples: Sequence[Mapping[str, Any]]) -> str:
    """Render retrieved past heals as a reference block, or "" when there are none.

    Empty must render to the empty string, not to an empty heading: the k=0 arm of the
    sweep has to reproduce the pre-memory prompt byte for byte, or it is a different
    experiment from the baseline it gets compared against.

    Entries carry structure and selectors only — never the anchor value. Showing the model
    a neighbour's correct answer would score as model skill on a corpus built from these
    same pages.
    """
    if not examples:
        return ""
    lines = "\n".join(
        f"  - {e.get('page_type', '?')} page, {e.get('drift_type', '?')} drift, "
        f"field {e.get('field_name', '?')} ({e.get('field_type', '?')}): "
        f"{e.get('old_selector', '?')} -> {e.get('healed_selector', '?')}"
        for e in examples
    )
    # No "these are different pages" disclaimer: under --partition loo the nearest neighbour is
    # the same base page under a different drift transform, so the sentence was false exactly
    # where it was most reassuring. A claim that has to be conditionally true is worth not making.
    return (
        "Selectors that repaired structurally similar pages before:\n"
        f"{lines}\n\n"
    )


def build_prompt(
    cleaned_html: str,
    fields: List[FieldSpec],
    failures: List[Failure],
    examples: Sequence[Mapping[str, Any]] = (),
) -> str:
    """Build the LLM prompt for selector healing.

    Args:
        cleaned_html: Output of ``clean_html()``.
        fields: All field specs (for context).
        failures: Fields that need new selectors.
        examples: Past heals retrieved from memory, best match first. Empty (the default)
            reproduces the pre-memory prompt exactly.

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
        f"{_render_examples(examples)}"
        "HTML (cleaned):\n"
        "```html\n"
        f"{cleaned_html}\n"
        "```\n\n"
        "Each new selector must resolve against the HTML above and must select the node "
        "whose text is the field's value. Prefer id, then data-* / itemprop / role, then a "
        "meaningful class; avoid positional paths.\n"
        "Respond with a JSON object mapping each field name to a new selector.\n"
        "Every selector MUST be prefixed with either 'css=' or 'xpath='.\n"
        # The example is deliberately generic. It used to read `css=.a-price-whole` /
        # `css=.pdp-product-name` — the literal correct answers for the drift fixture, which
        # would score as model skill on any benchmark built from that corpus.
        "Format example (do not copy these selectors):\n"
        '{"<field_name>": "css=#some-id", "<other_field>": "xpath=//tag[@data-x=\'y\']"}\n'
    )
