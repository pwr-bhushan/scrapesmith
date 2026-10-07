"""Heal graph: the retry loop's control flow with post_check faked, so no Playwright.

The fake gate reads verdicts from a table keyed by selector — the test decides which selectors
"work" and the graph has to find its way there through feedback.
"""
import tempfile
from pathlib import Path

import pytest

import app.heal_graph as hg
from spike.heal.provider import Failure, FieldSpec, HealProvider, Proposal

FIELDS_BY_NAME = {
    "price": {"name": "price", "dq": {"parses_as": "number"}, "anchor": {"value": "149900"}},
    "title": {"name": "title", "dq": {}, "anchor": {"value": "Phone"}},
}
SPECS = [FieldSpec(name=n, field_type="text", old_selector=f"css=.{n}") for n in FIELDS_BY_NAME]
FAILURES = [Failure(field_name=n, dq_status="empty") for n in FIELDS_BY_NAME]

# selector -> (status, reason, value)
GATE = {
    "css=.good-price": ("healed", "ok", "149900"),
    "css=.good-title": ("healed", "ok", "Phone"),
    "css=.decoy": ("suspect", "anchor check rejected the value '999'", "999"),
    "css=.nope": ("still_broken", "matched no element", None),
}


class ScriptedProvider(HealProvider):
    """Returns the n-th scripted answer on the n-th call and records every call."""

    name = "scripted"

    def __init__(self, script):
        self.script = script
        self.calls = []

    def propose(self, cleaned_html, fields, failures, examples=()):
        self.calls.append(list(failures))
        answer = self.script[min(len(self.calls), len(self.script)) - 1]
        return {
            f.field_name: Proposal(selector=answer[f.field_name])
            for f in failures
            if f.field_name in answer
        }


@pytest.fixture(autouse=True)
def fake_gate(monkeypatch):
    async def post_check(proposals, rep_path, cluster_paths, fields_by_name, render_js,
                         paths_by_filename=None):
        out = {}
        for name, sel in proposals.items():
            status, reason, value = GATE[sel]
            out[name] = {"selector": sel, "status": status, "value": value,
                         "anchor_ok": status == "healed", "reason": reason}
        return out

    monkeypatch.setattr(hg, "post_check", post_check)


async def _heal(provider, max_attempts=3):
    return await hg.heal_cluster(
        provider,
        cleaned_html="<html></html>",
        specs=SPECS,
        failures=FAILURES,
        rep_path="rep.html",
        fields_by_name=FIELDS_BY_NAME,
        max_attempts=max_attempts,
    )


async def test_first_try_heal_stops_after_one_attempt():
    p = ScriptedProvider([{"price": "css=.good-price", "title": "css=.good-title"}])
    out = await _heal(p)
    assert out["attempts"] == 1 and len(p.calls) == 1
    assert {v["status"] for v in out["proposals"].values()} == {"healed"}


async def test_retry_reaches_a_heal_and_only_reproposes_unhealed_fields():
    p = ScriptedProvider([
        {"price": "css=.nope", "title": "css=.good-title"},
        {"price": "css=.good-price"},
    ])
    out = await _heal(p)
    assert out["attempts"] == 2
    assert [f.field_name for f in p.calls[1]] == ["price"]  # title already healed
    assert out["proposals"]["price"]["selector"] == "css=.good-price"
    assert out["proposals"]["title"]["status"] == "healed"


async def test_feedback_carries_the_reason_and_never_the_anchor():
    p = ScriptedProvider([{"price": "css=.decoy"}, {"price": "css=.nope"}, {"price": "css=.nope"}])
    await _heal(p)
    second, third = p.calls[1][0].feedback, p.calls[2][0].feedback
    assert second == ("css=.decoy — anchor check rejected the value '999'",)
    assert len(third) == 2  # history accumulates so attempt 3 doesn't repeat attempt 1
    joined = " ".join(third)
    assert "149900" not in joined, "the anchor value must never reach the prompt (fork 1A)"


async def test_missing_proposal_is_retried_with_its_own_reason():
    p = ScriptedProvider([{}, {"price": "css=.good-price", "title": "css=.good-title"}])
    out = await _heal(p)
    assert p.calls[1][0].feedback == ("(no selector) — no selector was returned",)
    assert out["attempts"] == 2


async def test_best_verdict_is_kept_when_a_retry_does_worse():
    p = ScriptedProvider([{"price": "css=.decoy", "title": "css=.good-title"},
                          {"price": "css=.nope"}])
    out = await _heal(p, max_attempts=2)
    assert out["proposals"]["price"]["status"] == "suspect"
    assert out["proposals"]["price"]["selector"] == "css=.decoy"


async def test_max_attempts_one_is_a_single_propose_call():
    p = ScriptedProvider([{"price": "css=.nope", "title": "css=.nope"}])
    out = await _heal(p, max_attempts=1)
    assert len(p.calls) == 1 and out["attempts"] == 1
    assert all(f.feedback == () for f in p.calls[0])  # attempt 1 = the pre-graph prompt


async def test_never_healing_stops_at_max_attempts():
    p = ScriptedProvider([{"price": "css=.nope", "title": "css=.nope"}])
    out = await _heal(p, max_attempts=3)
    assert len(p.calls) == 3 and out["attempts"] == 3


async def test_unproposed_fields_are_left_out_of_the_output():
    p = ScriptedProvider([{"title": "css=.good-title"}])
    out = await _heal(p, max_attempts=1)
    assert set(out["proposals"]) == {"title"}


# ---- outer graph: detect → cluster → heal each ----

def _result(path, status):
    return {"file": Path(path).name, "path": path, "dom_skeleton_hash": "h1",
            "field_status": {"price": status, "title": "ok"}, "data": {}}


@pytest.fixture()
def page():
    f = tempfile.NamedTemporaryFile("w", suffix=".html", delete=False)
    f.write("<html><body><span class='good-price'>149900</span></body></html>")
    f.close()
    yield f.name
    Path(f.name).unlink(missing_ok=True)


async def test_no_drift_short_circuits(page):
    p = ScriptedProvider([{}])
    out = await hg.run_heal([_result(page, "ok")], list(FIELDS_BY_NAME.values()), p, False)
    assert out["triggered"] is False and p.calls == []


async def test_drift_runs_the_heal_loop_per_cluster(page):
    p = ScriptedProvider([{"price": "css=.nope"}, {"price": "css=.good-price"}])
    out = await hg.run_heal([_result(page, "empty")], list(FIELDS_BY_NAME.values()), p, False)
    assert out["triggered"] is True and out["failing"] == ["price"]
    (cl,) = out["clusters"]
    assert cl["attempts"] == 2 and cl["model"] == "scripted"
    assert cl["proposals"]["price"]["status"] == "healed"


async def test_no_provider_reports_unavailable(page):
    out = await hg.run_heal([_result(page, "empty")], list(FIELDS_BY_NAME.values()), None, False)
    (cl,) = out["clusters"]
    assert cl["model"] == "unavailable" and cl["proposals"] == {} and cl["attempts"] == 0


async def test_a_rejected_selector_outranks_no_selector():
    """Otherwise a late broken-but-resolving proposal is hidden as "no proposal", and the
    bench's resolve_but_wrong guard never sees it."""
    p = ScriptedProvider([{"title": "css=.good-title"}, {"price": "css=.nope"}])
    out = await _heal(p, max_attempts=2)
    assert out["proposals"]["price"]["selector"] == "css=.nope"
