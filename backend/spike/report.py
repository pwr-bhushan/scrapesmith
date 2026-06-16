"""Report renderer — CLI table and JSON/markdown artifact writer.

ponytail: stdlib json + string formatting only; no tabulate dependency.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict
from typing import Any, Dict, List

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
    lines.append("Phase 0 — Heal Spike Results")
    lines.append("=" * 72)
    lines.append(
        f"{'Provider':<24} {'Case':<20} {'Field':<10} {'Correct':<8} {'DQ':<12}"
    )
    lines.append("-" * 72)
    for r in results:
        correct_str = "YES" if r.anchor_correct else ("WRONG" if r.resolve_but_wrong else "NO")
        lines.append(
            f"{r.provider_name:<24} {r.case_id:<20} {r.field_name:<10} {correct_str:<8} {r.dq_status:<12}"
        )
    lines.append("=" * 72)
    lines.append(f"anchor_correct_rate  : {metrics['anchor_correct_rate']:.2%}")
    lines.append(f"resolve_but_wrong_rate: {metrics['resolve_but_wrong_rate']:.2%}")
    lines.append(f"no_proposal_rate     : {metrics['no_proposal_rate']:.2%}  (provider omitted or proposal rejected)")
    lines.append("")
    lines.append("Per-provider breakdown:")
    for pname, pmetrics in metrics.get("per_provider", {}).items():
        lines.append(
            f"  {pname}: anchor_correct={pmetrics['anchor_correct_rate']:.2%}"
            f"  ({pmetrics['anchor_correct']}/{pmetrics['total']})"
        )
    lines.append("=" * 72)
    return "\n".join(lines)


def write_artifacts(
    results: List[BenchResult],
    metrics: Dict[str, Any],
    output_dir: str = "artifacts",
) -> None:
    """Write JSON and Markdown report artifacts.

    Args:
        results: Output of ``run_bench()``.
        metrics: Output of ``compute_metrics()``.
        output_dir: Directory to write ``phase0_report.json`` and
            ``phase0_report.md`` into.
    """
    os.makedirs(output_dir, exist_ok=True)

    report_data = {
        "metrics": metrics,
        "results": [asdict(r) for r in results],
    }
    json_path = os.path.join(output_dir, "phase0_report.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)

    md_path = os.path.join(output_dir, "phase0_report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Phase 0 Heal Spike Report\n\n")
        f.write("## Summary\n\n")
        f.write(f"- **anchor_correct_rate**: {metrics['anchor_correct_rate']:.2%}\n")
        f.write(f"- **resolve_but_wrong_rate**: {metrics['resolve_but_wrong_rate']:.2%}\n")
        f.write(f"- **no_proposal_rate**: {metrics['no_proposal_rate']:.2%} (provider omitted or proposal rejected)\n\n")
        f.write("## Per-Provider\n\n")
        for pname, pm in metrics.get("per_provider", {}).items():
            f.write(
                f"- **{pname}**: {pm['anchor_correct_rate']:.2%} correct"
                f" ({pm['anchor_correct']}/{pm['total']})\n"
            )
        f.write("\n## Field Results\n\n")
        f.write("| Provider | Case | Field | Correct | DQ Status |\n")
        f.write("|---|---|---|---|---|\n")
        for r in results:
            correct_str = "YES" if r.anchor_correct else ("WRONG" if r.resolve_but_wrong else "NO")
            f.write(
                f"| {r.provider_name} | {r.case_id} | {r.field_name}"
                f" | {correct_str} | {r.dq_status} |\n"
            )
