"""Smoke tests for spike.report — render_table and write_artifacts.

L1: Guard the GATE deliverable artifact with a cheap smoke test.
"""
from __future__ import annotations

import json

from spike.bench import compute_metrics
from spike.report import render_table, write_artifacts


class TestReportSmoke:
    def test_render_table_on_empty_input_returns_nonempty_string(self):
        """render_table on empty results must return a non-empty string."""
        metrics = compute_metrics([])
        table = render_table([], metrics)
        assert isinstance(table, str)
        assert len(table) > 0

    def test_write_artifacts_creates_md_and_json(self, tmp_path):
        """write_artifacts must create phase0_report.md and phase0_report.json."""
        metrics = compute_metrics([])
        write_artifacts([], metrics, output_dir=str(tmp_path))
        assert (tmp_path / "phase0_report.md").exists()
        assert (tmp_path / "phase0_report.json").exists()

    def test_write_artifacts_json_round_trips(self, tmp_path):
        """JSON artifact must be valid JSON that round-trips cleanly."""
        metrics = compute_metrics([])
        write_artifacts([], metrics, output_dir=str(tmp_path))
        raw = (tmp_path / "phase0_report.json").read_text(encoding="utf-8")
        parsed = json.loads(raw)
        assert "metrics" in parsed
        assert "results" in parsed

    def test_arm_is_recorded_in_both_artifacts(self, tmp_path):
        """A k>0 report must not be indistinguishable from a k=0 one on disk."""
        metrics = compute_metrics([])
        arm = {"provider": "ollama", "k": 3, "partition": "lobo", "memory_entries": 46}
        write_artifacts([], metrics, output_dir=str(tmp_path), arm=arm)
        parsed = json.loads((tmp_path / "phase0_report.json").read_text(encoding="utf-8"))
        assert parsed["arm"] == arm
        assert "k=3" in (tmp_path / "phase0_report.md").read_text(encoding="utf-8")

    def test_arm_defaults_to_empty_and_adds_no_markdown(self, tmp_path):
        """Omitting arm must leave the k=0 artifact shape the older reports were written in."""
        metrics = compute_metrics([])
        write_artifacts([], metrics, output_dir=str(tmp_path))
        parsed = json.loads((tmp_path / "phase0_report.json").read_text(encoding="utf-8"))
        assert parsed["arm"] == {}
        md = (tmp_path / "phase0_report.md").read_text(encoding="utf-8")
        assert md.startswith("# Heal Bench Report\n\n## Summary\n\n")
