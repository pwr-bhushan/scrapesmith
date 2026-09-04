"""Tests for spike.bench — metric math with FakeProvider.

Core contract:
  - anchor_correct_rate = (# anchor-correct fields) / (# total fields)
  - 1 correct of 2 → exactly 0.5
  - 0 correct → 0.0
  - All correct → 1.0
  - resolve-but-wrong-value counted separately

All tests use FakeProvider + synthetic BenchCases (no network, no model).
All tests must FAIL (RED) until Step 3 implements compute_metrics().
"""
from __future__ import annotations

import pytest

from spike.bench import BenchCase, BenchResult, compute_metrics, load_case
from spike.heal.provider import HealProvider, Proposal

# ---------------------------------------------------------------------------
# FakeProvider for bench tests
# ---------------------------------------------------------------------------

class FakeProvider(HealProvider):
    """Controlled fake: caller supplies the mapping of field → selector."""

    def __init__(self, canned: dict[str, str]) -> None:
        # canned: field_name → selector string (must be prefixed)
        self._canned = canned

    @property
    def name(self) -> str:
        return "fake"

    def propose(self, cleaned_html, fields, failures):
        return {
            f.field_name: Proposal(selector=self._canned[f.field_name])
            for f in failures
            if f.field_name in self._canned
        }


# ---------------------------------------------------------------------------
# Synthetic BenchResult helpers
# ---------------------------------------------------------------------------

def _make_result(
    *,
    provider_name: str = "fake",
    case_id: str = "case1",
    field_name: str = "price",
    anchor: str = "₹1,49,900",
    anchor_correct: bool,
    resolve_but_wrong: bool = False,
    dq_status: str = "ok",
    proposed_selector: str | None = "css=.price",
    resolved_values: list[str] | None = None,
    status: str = "unchecked",
    drift_type: str = "unlabelled",
) -> BenchResult:
    return BenchResult(
        provider_name=provider_name,
        case_id=case_id,
        field_name=field_name,
        proposed_selector=proposed_selector,
        resolved_values=resolved_values or (["₹1,49,900"] if anchor_correct else []),
        anchor=anchor,
        anchor_correct=anchor_correct,
        resolve_but_wrong=resolve_but_wrong,
        dq_status=dq_status,
        status=status,
        drift_type=drift_type,
    )


# ---------------------------------------------------------------------------
# Test: anchor_correct_rate arithmetic
# ---------------------------------------------------------------------------

class TestAnchorCorrectRate:
    def test_one_correct_of_two_is_half(self):
        """1 correct of 2 fields → anchor_correct_rate == 0.5 exactly."""
        results = [
            _make_result(field_name="price", anchor_correct=True),
            _make_result(field_name="title", anchor_correct=False),
        ]
        metrics = compute_metrics(results)
        assert metrics["anchor_correct_rate"] == pytest.approx(0.5)

    def test_all_correct_is_one(self):
        """All fields correct → anchor_correct_rate == 1.0."""
        results = [
            _make_result(field_name="price", anchor_correct=True),
            _make_result(field_name="title", anchor_correct=True),
        ]
        metrics = compute_metrics(results)
        assert metrics["anchor_correct_rate"] == pytest.approx(1.0)

    def test_none_correct_is_zero(self):
        """No fields correct → anchor_correct_rate == 0.0."""
        results = [
            _make_result(field_name="price", anchor_correct=False),
            _make_result(field_name="title", anchor_correct=False),
        ]
        metrics = compute_metrics(results)
        assert metrics["anchor_correct_rate"] == pytest.approx(0.0)

    def test_empty_results_returns_zero(self):
        """Empty results list → anchor_correct_rate == 0.0 (not division error)."""
        metrics = compute_metrics([])
        assert metrics["anchor_correct_rate"] == pytest.approx(0.0)

    def test_three_of_four_correct(self):
        """3 of 4 correct → 0.75."""
        results = [
            _make_result(field_name="a", anchor_correct=True),
            _make_result(field_name="b", anchor_correct=True),
            _make_result(field_name="c", anchor_correct=True),
            _make_result(field_name="d", anchor_correct=False),
        ]
        metrics = compute_metrics(results)
        assert metrics["anchor_correct_rate"] == pytest.approx(0.75)


# ---------------------------------------------------------------------------
# Test: resolve-but-wrong-value rate
# ---------------------------------------------------------------------------

class TestResolvesButWrongRate:
    def test_resolve_but_wrong_counted(self):
        """resolve_but_wrong=True fields must be counted in resolve_but_wrong_rate."""
        results = [
            _make_result(
                field_name="price",
                anchor_correct=False,
                resolve_but_wrong=True,
                resolved_values=["₹9,99,999"],  # resolved but wrong value
                dq_status="ok",
            ),
            _make_result(
                field_name="title",
                anchor_correct=True,
                resolve_but_wrong=False,
            ),
        ]
        metrics = compute_metrics(results)
        # 1 resolve-but-wrong out of 2 total fields
        assert metrics["resolve_but_wrong_rate"] == pytest.approx(0.5)

    def test_no_resolve_but_wrong(self):
        """With no resolve-but-wrong results, rate must be 0.0."""
        results = [
            _make_result(field_name="price", anchor_correct=True),
            _make_result(field_name="title", anchor_correct=True),
        ]
        metrics = compute_metrics(results)
        assert metrics["resolve_but_wrong_rate"] == pytest.approx(0.0)

    def test_dq_failing_wrong_resolution_counted_as_resolve_but_wrong(self):
        """H1: a selector that resolves to a DQ-failing wrong value IS resolve_but_wrong.

        Previously the narrow definition only counted DQ-passing wrong values.
        The fix widens: any non-empty resolution that is not anchor-correct counts,
        regardless of dq_status.
        """
        # Simulate: resolved a value, DQ fails, not anchor-correct → resolve_but_wrong=True
        result = BenchResult(
            provider_name="fake",
            case_id="case1",
            field_name="price",
            proposed_selector="css=.price",
            resolved_values=["GARBAGE"],   # resolved but wrong (and would fail DQ)
            anchor="₹1,49,900",
            anchor_correct=False,
            resolve_but_wrong=True,        # widened definition
            dq_status="regex_fail",
        )
        metrics = compute_metrics([result])
        assert metrics["resolve_but_wrong_rate"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Test: no_proposal_rate (H2 — renamed from parse_fail_rate)
# ---------------------------------------------------------------------------

class TestNoProposalRate:
    def test_no_proposal_rate_key_present(self):
        """H2: compute_metrics must return 'no_proposal_rate' key (not parse_fail_rate)."""
        metrics = compute_metrics([])
        assert "no_proposal_rate" in metrics
        assert "parse_fail_rate" not in metrics

    def test_no_proposal_rate_counts_missing_selector(self):
        """H2: proposed_selector=None increments no_proposal_rate."""
        results = [
            _make_result(
                field_name="price",
                anchor_correct=False,
                proposed_selector=None,
                resolved_values=[],
                dq_status="empty",
            ),
            _make_result(
                field_name="title",
                anchor_correct=True,
            ),
        ]
        metrics = compute_metrics(results)
        # 1 of 2 fields had no proposal
        assert metrics["no_proposal_rate"] == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Test: per_provider breakdown
# ---------------------------------------------------------------------------

class TestPerProviderBreakdown:
    def test_per_provider_key_present(self):
        """compute_metrics must return a 'per_provider' dict."""
        results = [_make_result(provider_name="fake", anchor_correct=True)]
        metrics = compute_metrics(results)
        assert "per_provider" in metrics

    def test_per_provider_correct_rate_for_one_provider(self):
        """per_provider must include the anchor_correct_rate for the fake provider."""
        results = [
            _make_result(provider_name="fake", field_name="price", anchor_correct=True),
            _make_result(provider_name="fake", field_name="title", anchor_correct=False),
        ]
        metrics = compute_metrics(results)
        assert "fake" in metrics["per_provider"]
        assert metrics["per_provider"]["fake"]["anchor_correct_rate"] == pytest.approx(0.5)

    def test_multiple_providers_separated(self):
        """Results from two different providers must be broken down independently."""
        results = [
            _make_result(provider_name="providerA", field_name="price", anchor_correct=True),
            _make_result(provider_name="providerA", field_name="title", anchor_correct=True),
            _make_result(provider_name="providerB", field_name="price", anchor_correct=False),
            _make_result(provider_name="providerB", field_name="title", anchor_correct=False),
        ]
        metrics = compute_metrics(results)
        assert metrics["per_provider"]["providerA"]["anchor_correct_rate"] == pytest.approx(1.0)
        assert metrics["per_provider"]["providerB"]["anchor_correct_rate"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Test: load_case (fixture loading)
# ---------------------------------------------------------------------------

class TestLoadCase:
    def test_load_case_returns_bench_case(self, amazon_case_dir):
        """load_case must return a BenchCase with correct shape."""
        case = load_case(str(amazon_case_dir))
        assert isinstance(case, BenchCase)
        assert case.host == "amazon.in"
        assert case.page_type == "product_listing"
        assert len(case.fields) == 2

    def test_load_case_fields_have_anchor(self, amazon_case_dir):
        """Each field in the loaded BenchCase must have a non-empty anchor."""
        case = load_case(str(amazon_case_dir))
        for field in case.fields:
            assert field.anchor, f"Field '{field.name}' has no anchor"

    def test_load_case_before_after_html_loaded(self, amazon_case_dir):
        """BenchCase must contain the before_html and after_html strings."""
        case = load_case(str(amazon_case_dir))
        assert "₹1,49,900" in case.before_html
        assert "₹ 1,49,900" in case.after_html or "1,49,900" in case.after_html


# ---------------------------------------------------------------------------
# Test: tiered scoring — healed_rate (DECISION 4c)
#
# Success is "the right value AND the product's gate accepted it". Both halves are
# load-bearing: a correct value that post_check marks `suspect` is never auto-applied,
# so counting it as a heal overstates what would actually ship.
# ---------------------------------------------------------------------------

class TestHealedRate:
    def test_healed_requires_both_anchor_correct_and_gate(self):
        """anchor_correct alone is not a heal; the gate must also say 'healed'."""
        results = [
            _make_result(field_name="a", anchor_correct=True, status="healed"),
            _make_result(field_name="b", anchor_correct=True, status="suspect"),
        ]
        metrics = compute_metrics(results)
        assert metrics["anchor_correct_rate"] == pytest.approx(1.0)
        assert metrics["healed_rate"] == pytest.approx(0.5)

    def test_gate_healed_but_wrong_value_is_not_a_heal(self):
        """The gate passing on a wrong value must not count — that is the dangerous case."""
        results = [_make_result(field_name="a", anchor_correct=False, status="healed")]
        assert compute_metrics(results)["healed_rate"] == pytest.approx(0.0)

    def test_healed_rate_present_on_empty(self):
        assert compute_metrics([])["healed_rate"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Test: per_drift_type breakdown (DECISION 1 — the labelled corpus pays off here)
# ---------------------------------------------------------------------------

class TestPerDriftType:
    def test_drift_types_broken_down_independently(self):
        results = [
            _make_result(field_name="a", anchor_correct=True, status="healed",
                         drift_type="class_rename"),
            _make_result(field_name="b", anchor_correct=True, status="healed",
                         drift_type="class_rename"),
            _make_result(field_name="c", anchor_correct=False, drift_type="combo"),
            _make_result(field_name="d", anchor_correct=False, drift_type="combo"),
        ]
        per_drift = compute_metrics(results)["per_drift_type"]
        assert per_drift["class_rename"]["healed_rate"] == pytest.approx(1.0)
        assert per_drift["combo"]["healed_rate"] == pytest.approx(0.0)
        assert per_drift["combo"]["total"] == 2

    def test_unlabelled_default_keeps_legacy_cases_countable(self):
        """Cases predating the mutator have no drift_type and must still be reported."""
        per_drift = compute_metrics([_make_result(anchor_correct=True)])["per_drift_type"]
        assert per_drift["unlabelled"]["total"] == 1


# ---------------------------------------------------------------------------
# Test: the generated corpus loads and is labelled
# ---------------------------------------------------------------------------

class TestGeneratedCorpus:
    def test_every_generated_case_is_labelled_and_loads(self, drift_dir):
        dirs = [d for d in sorted(drift_dir.iterdir()) if (d / "case.json").is_file()]
        cases = [load_case(str(d)) for d in dirs]
        assert len(cases) >= 15, f"corpus too small to measure a rate: {len(cases)} cases"
        for case in cases:
            assert case.fields, f"{case.case_id} has no fields to heal"
            assert case.drift_type, f"{case.case_id} has no drift_type"

    def test_old_selectors_are_actually_broken(self, drift_dir):
        """A case where the old selector still works has nothing to heal and would
        inflate the rate. Checked with soup.select, the same engine the generator used."""
        from bs4 import BeautifulSoup

        for case_dir in sorted(drift_dir.iterdir()):
            if not (case_dir / "case.json").is_file():
                continue
            case = load_case(str(case_dir))
            if case.drift_type == "unlabelled":
                continue  # hand-written case; its selectors are not all plain CSS
            soup = BeautifulSoup(case.after_html, "html.parser")
            for field in case.fields:
                sel = field.old_selector.removeprefix("css=")
                assert not soup.select(sel), (
                    f"{case.case_id}/{field.name}: old selector {sel!r} still resolves"
                )
