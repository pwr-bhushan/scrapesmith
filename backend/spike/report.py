"""Report renderer — CLI table and JSON/markdown artifact writer.

ponytail: stdlib json + string formatting only; no tabulate dependency.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from spike.bench import BenchResult


def render_table(results: List[BenchResult], metrics: Dict[str, Any]) -> str:
    """Render a CLI-friendly results table.

    Args:
        results: Output of ``run_bench()``.
        metrics: Output of ``compute_metrics()``.

    Returns:
        Multi-line string suitable for printing to stdout.
    """
    lines: List[str] = []
    lines.append("=" * 72)
    lines.append("Heal Bench — selector repair over the drift corpus")
    lines.append("=" * 72)
    lines.append(
        f"{'Case':<28} {'Field':<14} {'Correct':<8} {'Gate':<13} {'DQ':<10}"
    )
    lines.append("-" * 72)
    for r in results:
        lines.append(
            f"{r.case_id:<28} {r.field_name:<14} {_verdict(r):<8} {r.status:<13} {r.dq_status:<10}"
        )
    lines.append("=" * 72)
    # healed_rate leads: it is the only rate that describes what would actually ship.
    lines.append(f"healed_rate           : {metrics.get('healed_rate', 0.0):.2%}  (correct AND accepted by post_check)")
    lines.append(f"anchor_correct_rate   : {metrics['anchor_correct_rate']:.2%}")
    lines.append(f"resolve_but_wrong_rate: {metrics['resolve_but_wrong_rate']:.2%}  (guard — a rise here is a regression)")
    lines.append(f"no_proposal_rate      : {metrics['no_proposal_rate']:.2%}  (provider omitted or proposal rejected)")
    for title, key in (("Per-provider", "per_provider"), ("Per drift type", "per_drift_type")):
        rows = metrics.get(key) or {}
        if not rows:
            continue
        lines.append("")
        lines.append(f"{title}:")
        for label, m in rows.items():
            lines.append(
                f"  {label:<20} healed={m.get('healed_rate', 0.0):>7.2%}"
                f"  correct={m['anchor_correct_rate']:>7.2%}"
                f"  wrong={m.get('resolve_but_wrong_rate', 0.0):>7.2%}"
                f"  (n={m['total']})"
            )
    lines.append("=" * 72)
    return "\n".join(lines)


def _verdict(r: BenchResult) -> str:
    """One word for whether the model got the value right."""
    if r.anchor_correct:
        return "YES"
    return "WRONG" if r.resolve_but_wrong else "NO"


def write_artifacts(
    results: List[BenchResult],
    metrics: Dict[str, Any],
    output_dir: str = "artifacts",
    arm: Optional[Dict[str, Any]] = None,
) -> None:
    """Write JSON and Markdown report artifacts.

    Args:
        results: Output of ``run_bench()``.
        metrics: Output of ``compute_metrics()``.
        output_dir: Directory to write ``phase0_report.json`` and
            ``phase0_report.md`` into.
        arm: Which experiment produced these numbers (k, partition, memory size,
            provider). Without it a k=5 report is byte-indistinguishable from a k=0
            one, and a k-curve assembled from unlabelled files is unfalsifiable.
    """
    os.makedirs(output_dir, exist_ok=True)

    report_data = {
        "arm": arm or {},
        "metrics": metrics,
        "results": [asdict(r) for r in results],
    }
    json_path = os.path.join(output_dir, "phase0_report.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)

    md_path = os.path.join(output_dir, "phase0_report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Heal Bench Report\n\n")
        if arm:
            f.write("`" + "  ".join(f"{k}={v}" for k, v in arm.items()) + "`\n\n")
        f.write("## Summary\n\n")
        f.write(
            f"- **healed_rate**: {metrics.get('healed_rate', 0.0):.2%}"
            " — anchor-correct **and** accepted by `post_check`. Headline: what would ship.\n"
        )
        f.write(f"- **anchor_correct_rate**: {metrics['anchor_correct_rate']:.2%} — the model got the right value.\n")
        f.write(
            f"- **resolve_but_wrong_rate**: {metrics['resolve_but_wrong_rate']:.2%}"
            " — guard: a rise here counts as a regression even if `healed_rate` also rises.\n"
        )
        f.write(f"- **no_proposal_rate**: {metrics['no_proposal_rate']:.2%} (provider omitted or proposal rejected)\n")
        for title, key in (("Per-Provider", "per_provider"), ("Per Drift Type", "per_drift_type")):
            rows = metrics.get(key) or {}
            if not rows:
                continue
            f.write(f"\n## {title}\n\n")
            f.write("| | healed | anchor-correct | resolve-but-wrong | n |\n")
            f.write("|---|---|---|---|---|\n")
            for label, m in rows.items():
                f.write(
                    f"| {label} | {m.get('healed_rate', 0.0):.2%} | {m['anchor_correct_rate']:.2%}"
                    f" | {m.get('resolve_but_wrong_rate', 0.0):.2%} | {m['total']} |\n"
                )
        f.write("\n## Field Results\n\n")
        f.write("| Case | Field | Drift | Correct | Gate | DQ | Selector |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for r in results:
            f.write(
                f"| {r.case_id} | {r.field_name} | {r.drift_type} | {_verdict(r)}"
                f" | {r.status} | {r.dq_status} | `{r.proposed_selector or '—'}` |\n"
            )
