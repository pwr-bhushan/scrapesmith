"""Bench harness — loads fixtures × providers and computes metrics.

Public API:
  BenchCase: dataclass loaded from case.json
  BenchResult: result for one provider × one case × one field
  run_bench(cases, providers) -> list[BenchResult]
  compute_metrics(results) -> dict  # includes anchor_correct_rate

ponytail: stdlib json/pathlib only; compute_metrics is arithmetic over lists.
"""
from __future__ import annotations

import json
import pathlib
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class FieldCase:
    """One field from case.json."""
    name: str
    field_type: str
    old_selector: str
    dq: Dict[str, Any]
    anchor: str


@dataclass
class BenchCase:
    """One drift fixture case."""
    case_id: str
    host: str
    page_type: str
    before_html: str
    after_html: str
    fields: List[FieldCase]


@dataclass
class BenchResult:
    """Result for one provider × one case × one field."""
    provider_name: str
    case_id: str
    field_name: str
    proposed_selector: Optional[str]
    resolved_values: List[str]
    anchor: str
    anchor_correct: bool
    resolve_but_wrong: bool   # resolved ≥1 value but != anchor
    dq_status: str
    latency_ms: float = 0.0


def load_case(case_dir: str) -> BenchCase:
    """Load a BenchCase from a fixture directory.

    Args:
        case_dir: Path to the fixture directory containing before.html,
            after.html, and case.json.

    Returns:
        A populated ``BenchCase``.
    """
    base = pathlib.Path(case_dir)
    case_id = base.name
    meta = json.loads((base / "case.json").read_text(encoding="utf-8"))
    before_html = (base / "before.html").read_text(encoding="utf-8")
    after_html = (base / "after.html").read_text(encoding="utf-8")

    fields = [
        FieldCase(
            name=f["name"],
            field_type=f["type"],
            old_selector=f["old_selector"],
            dq=f["dq"],
            anchor=f["anchor"],
        )
        for f in meta["fields"]
    ]

    return BenchCase(
        case_id=case_id,
        host=meta["host"],
        page_type=meta["page_type"],
        before_html=before_html,
        after_html=after_html,
        fields=fields,
    )


def run_bench(
    cases: List[BenchCase],
    providers: List[Any],  # List[HealProvider] — loosely typed
) -> List[BenchResult]:
    """Run all providers against all cases.

    Args:
        cases: List of ``BenchCase`` objects.
        providers: List of ``HealProvider`` instances.

    Returns:
        Flat list of ``BenchResult`` objects (one per provider×case×field).
    """
    from spike.cleaner import clean_html
    from spike.dq import DQRule, check_dq
    from spike.heal.provider import Failure, FieldSpec
    from spike.resolve import normalize, resolve_selector

    results: List[BenchResult] = []

    for case in cases:
        for provider in providers:
            provider_name = getattr(provider, "name", type(provider).__name__)

            # Build failures list: treat all fields as failed (spike: all need healing)
            field_specs = [
                FieldSpec(
                    name=fc.name,
                    field_type=fc.field_type,
                    old_selector=fc.old_selector,
                )
                for fc in case.fields
            ]
            failures = [
                Failure(field_name=fc.name, dq_status="empty")
                for fc in case.fields
            ]

            cleaned = clean_html(case.after_html)

            t0 = time.monotonic()
            proposals = provider.propose(cleaned, field_specs, failures)
            latency_ms = (time.monotonic() - t0) * 1000

            for fc in case.fields:
                proposal = proposals.get(fc.name)
                proposed_selector = proposal.selector if proposal else None

                resolved_values: List[str] = []
                if proposed_selector:
                    try:
                        resolved_values = resolve_selector(case.after_html, proposed_selector)
                    except Exception:
                        resolved_values = []

                # DQ check on first resolved value
                first_value = resolved_values[0] if resolved_values else None
                dq_rule = DQRule(
                    required=fc.dq.get("required", True),
                    regex=fc.dq.get("regex"),
                    parses_as=fc.dq.get("parses_as"),
                )
                dq_status = check_dq(first_value, dq_rule)

                # Anchor-correct: resolved, DQ passes, and value equals anchor
                anchor_correct = False
                if resolved_values and dq_status == "ok":
                    norm_extracted = normalize(first_value or "", fc.field_type)
                    norm_anchor = normalize(fc.anchor, fc.field_type)
                    if norm_extracted == norm_anchor:
                        anchor_correct = True

                # resolve_but_wrong: resolved ≥1 value AND not anchor-correct,
                # independent of dq_status — catches DQ-failing wrong values too.
                # This is the "resolves but wrong" gate metric (§10 step 5 widened).
                resolve_but_wrong = bool(resolved_values) and not anchor_correct

                results.append(BenchResult(
                    provider_name=provider_name,
                    case_id=case.case_id,
                    field_name=fc.name,
                    proposed_selector=proposed_selector,
                    resolved_values=resolved_values,
                    anchor=fc.anchor,
                    anchor_correct=anchor_correct,
                    resolve_but_wrong=resolve_but_wrong,
                    dq_status=dq_status,
                    latency_ms=latency_ms,
                ))

    return results


def compute_metrics(results: List[BenchResult]) -> Dict[str, Any]:
    """Compute aggregate metrics from bench results.

    Returns a dict with at least:
      - ``anchor_correct_rate``: float (# anchor-correct / # total fields)
      - ``resolve_but_wrong_rate``: float
      - ``no_proposal_rate``: float — provider omitted or proposal rejected, not Playwright parse failure
      - ``per_provider``: dict[str, dict] with per-provider breakdowns

    Args:
        results: Output of ``run_bench()``.

    Returns:
        Metrics dict.
    """
    total = len(results)

    if total == 0:
        return {
            "anchor_correct_rate": 0.0,
            "resolve_but_wrong_rate": 0.0,
            "no_proposal_rate": 0.0,  # provider omitted or proposal rejected, not Playwright parse failure
            "per_provider": {},
        }

    n_correct = sum(1 for r in results if r.anchor_correct)
    n_wrong = sum(1 for r in results if r.resolve_but_wrong)
    n_no_proposal = sum(1 for r in results if r.proposed_selector is None)

    # Per-provider breakdown
    by_provider: Dict[str, List[BenchResult]] = defaultdict(list)
    for r in results:
        by_provider[r.provider_name].append(r)

    per_provider: Dict[str, Dict[str, Any]] = {}
    for pname, presults in by_provider.items():
        ptotal = len(presults)
        pcorrect = sum(1 for r in presults if r.anchor_correct)
        pwrong = sum(1 for r in presults if r.resolve_but_wrong)
        per_provider[pname] = {
            "anchor_correct_rate": pcorrect / ptotal if ptotal else 0.0,
            "resolve_but_wrong_rate": pwrong / ptotal if ptotal else 0.0,
            "total": ptotal,
            "anchor_correct": pcorrect,
        }

    return {
        "anchor_correct_rate": n_correct / total,
        "resolve_but_wrong_rate": n_wrong / total,
        "no_proposal_rate": n_no_proposal / total,  # provider omitted or proposal rejected, not Playwright parse failure
        "per_provider": per_provider,
    }
