"""Tests for spike.heal.prompt.build_prompt — the k=0 lock and the few-shot block.

Core contract:
  - build_prompt(h, f, fl) and build_prompt(h, f, fl, examples=()) are byte-identical
  - both equal tests/golden/prompt_k0.txt, captured from HEAD before B2.3
  - non-empty examples add a reference block naming old→healed selectors
  - no anchor value ever reaches the prompt, at any k

All tests must FAIL (RED) until B2.3 adds the `examples` parameter.
"""
from __future__ import annotations

import pathlib

from spike.bench import load_case
from spike.cleaner import clean_html
from spike.heal.prompt import build_prompt
from spike.heal.provider import Failure, FieldSpec

GOLDEN = pathlib.Path(__file__).parent / "golden" / "prompt_k0.txt"
GOLDEN_CASE = "product__combo"

SAMPLE_FIELDS = [
    FieldSpec(name="price", field_type="currency", old_selector="css=[data-price-amount]"),
    FieldSpec(name="title", field_type="text", old_selector="css=.product-title"),
]
SAMPLE_FAILURES = [
    Failure(field_name="price", dq_status="empty"),
    Failure(field_name="title", dq_status="empty"),
]
CLEANED_HTML = "<div class='price'>₹1,49,900</div><h2 class='name'>MacBook</h2>"

# Two memory entries in the shape B2.2 stores. Note what is absent: no anchor, no HTML.
EXAMPLES = [
    {
        "case_id": "job__class_rename",
        "host": "example-jobs.test",
        "page_type": "job",
        "drift_type": "class_rename",
        "field_name": "salary",
        "field_type": "currency",
        "old_selector": "css=.salary-amount",
        "healed_selector": "css=[itemprop='baseSalary']",
        "signature": {"html>body>main>div>span": 3, "@itemprop": 2},
    },
    {
        "case_id": "event__wrapper_insert",
        "host": "example-events.test",
        "page_type": "event",
        "drift_type": "wrapper_insert",
        "field_name": "price",
        "field_type": "currency",
        "old_selector": "css=.ticket-price",
        "healed_selector": "css=[data-ticket-price]",
        "signature": {"html>body>div>div>span": 4, "@data-ticket-price": 1},
    },
]


def _golden_inputs():
    """Rebuild the exact inputs the golden file was captured from."""
    case = load_case(str(pathlib.Path(__file__).parent.parent / "fixtures" / "drift" / GOLDEN_CASE))
    fields = [
        FieldSpec(name=f.name, field_type=f.field_type, old_selector=f.old_selector)
        for f in case.fields
    ]
    failures = [Failure(field_name=f.name, dq_status="empty") for f in case.fields]
    return clean_html(case.after_html), fields, failures, case


# ---------------------------------------------------------------------------
# The k=0 lock — the single most load-bearing test in B2
# ---------------------------------------------------------------------------

class TestK0PromptIsUnchanged:
    """If k=0 does not reproduce today's prompt byte for byte, the sweep's baseline
    arm is a *different experiment* from the B1 baseline it is compared against, and
    every k-curve drawn from it is meaningless. The golden file was captured from HEAD
    before prompt.py was touched, so this catches even a whitespace drift.
    """

    def test_default_call_matches_golden(self):
        cleaned, fields, failures, _ = _golden_inputs()
        assert build_prompt(cleaned, fields, failures) == GOLDEN.read_text(encoding="utf-8")

    def test_empty_examples_is_byte_identical_to_default(self):
        cleaned, fields, failures, _ = _golden_inputs()
        assert (
            build_prompt(cleaned, fields, failures, examples=())
            == build_prompt(cleaned, fields, failures)
        )

    def test_examples_defaults_to_empty(self):
        """The parameter must default to empty, so existing call sites keep k=0 behaviour."""
        import inspect

        default = inspect.signature(build_prompt).parameters["examples"].default
        assert not default, f"examples must default to something falsy, got {default!r}"


# ---------------------------------------------------------------------------
# The few-shot block
# ---------------------------------------------------------------------------

class TestExamplesBlock:
    def test_examples_render_old_and_healed_selectors(self):
        prompt = build_prompt(CLEANED_HTML, SAMPLE_FIELDS, SAMPLE_FAILURES, examples=EXAMPLES)
        for ex in EXAMPLES:
            assert ex["old_selector"] in prompt
            assert ex["healed_selector"] in prompt

    def test_examples_do_not_displace_the_original_prompt(self):
        """The reference block is additive: instructions and HTML must survive."""
        base = build_prompt(CLEANED_HTML, SAMPLE_FIELDS, SAMPLE_FAILURES)
        withex = build_prompt(CLEANED_HTML, SAMPLE_FIELDS, SAMPLE_FAILURES, examples=EXAMPLES)
        assert CLEANED_HTML in withex
        assert "Every selector MUST be prefixed" in withex
        assert len(withex) > len(base)

    def test_examples_block_absent_when_empty(self):
        """Whatever heading marks the block, it cannot appear at k=0 — enforced
        structurally by the byte-identity test above, and named here for intent."""
        base = build_prompt(CLEANED_HTML, SAMPLE_FIELDS, SAMPLE_FAILURES)
        withex = build_prompt(CLEANED_HTML, SAMPLE_FIELDS, SAMPLE_FAILURES, examples=EXAMPLES)
        added = withex.replace(base[: base.index("HTML (cleaned):")], "")
        assert added, "examples must add text"
        assert "css=.salary-amount" not in base


class TestNoAnchorLeak:
    """Defence in depth. A memory entry carries no anchor by construction (B2.2 test),
    but the prompt is the place where a leak would actually score as model skill, so
    it is asserted here too against the real corpus.
    """

    def test_no_corpus_anchor_appears_in_a_few_shot_prompt(self):
        cleaned, fields, failures, case = _golden_inputs()
        prompt = build_prompt(cleaned, fields, failures, examples=EXAMPLES)
        for ex in EXAMPLES:
            for value in ex.values():
                assert "₹" not in str(value), f"anchor-shaped value in example: {value!r}"
        # The page's own anchors legitimately appear inside the cleaned HTML; what must not
        # happen is an anchor arriving via the examples block.
        block = prompt.replace(cleaned, "")
        for field in case.fields:
            assert field.anchor not in block, (
                f"anchor {field.anchor!r} leaked into the prompt outside the page HTML"
            )
