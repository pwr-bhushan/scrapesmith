"""The self-healing loop as a LangGraph state graph (Section D).

Two compiled graphs:

- ``HEAL_GRAPH`` — one cluster: propose → validate → (retry → propose)* → END. The bench invokes
  this directly, so it measures the loop that ships.
- ``DRIFT_GRAPH`` — a batch: detect → cluster → heal each cluster (via ``HEAL_GRAPH``) → END.
  ``/heal/propose`` invokes this.

A retry tells the model which selector it tried and why the gate rejected it — never the anchor
value, so the anchor check stays independent of the prompt (fork 1A). The graph stops at
proposals: accepting one is a separate, human- or MCP-gated step.
"""
from __future__ import annotations

import asyncio
import dataclasses
import operator
import time
from pathlib import Path
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.aggregate import field_rates
from app.heal import cluster_failures, failing_fields, post_check

DEFAULT_MAX_ATTEMPTS = 3
_RANK = {"healed": 2, "suspect": 1, "still_broken": 0}


class HealState(TypedDict, total=False):
    provider: Any
    cleaned_html: str
    specs: list
    failures: list  # spike Failure — the fields still to heal, with their feedback
    examples: list
    rep_path: str
    cluster_paths: list
    fields_by_name: dict
    render_js: bool
    paths_by_filename: dict | None
    max_attempts: int
    attempt: int
    selectors: dict  # this attempt's proposals, {field: selector}
    latest: dict  # this attempt's verdicts, including "no selector" ones
    verdicts: dict  # best verdict per field across attempts
    model_ms: float


async def _propose(state: HealState) -> dict:
    provider, failures = state["provider"], state["failures"]
    args = (state["cleaned_html"], state["specs"], failures)
    examples = state["examples"]
    t0 = time.monotonic()
    # Positional when there is nothing to retrieve, so a provider written against the
    # 3-argument signature still works and attempt 1 matches the pre-graph call exactly.
    if examples:
        proposals = await asyncio.to_thread(provider.propose, *args, examples=examples)
    else:
        proposals = await asyncio.to_thread(provider.propose, *args)
    elapsed = (time.monotonic() - t0) * 1000

    selectors = {
        f.field_name: proposals[f.field_name].selector
        for f in failures
        if getattr(proposals.get(f.field_name), "selector", None)
    }
    return {
        "attempt": state.get("attempt", 0) + 1,
        "model_ms": state.get("model_ms", 0.0) + elapsed,
        "selectors": selectors,
    }


def _no_selector() -> dict:
    return {"selector": None, "status": "still_broken", "value": None, "anchor_ok": None,
            "reason": "no selector was returned"}


async def _validate(state: HealState) -> dict:
    latest = {f.field_name: _no_selector() for f in state["failures"]}
    selectors = state["selectors"]
    if selectors:
        latest |= await post_check(
            selectors,
            state["rep_path"],
            state["cluster_paths"],
            state["fields_by_name"],
            state["render_js"],
            state["paths_by_filename"],
        )

    best = dict(state.get("verdicts") or {})
    for name, verdict in latest.items():
        # strictly better only: on a tie the earlier attempt stands
        if name not in best or _rank(verdict) > _rank(best[name]):
            best[name] = verdict
    return {"latest": latest, "verdicts": best}


def _rank(verdict: dict) -> int:
    # a selector the gate rejected still outranks none: the bench's wrong-value guard has to
    # see it, and a reviewer can at least read why it failed
    return -1 if verdict["selector"] is None else _RANK[verdict["status"]]


def _retry(state: HealState) -> dict:
    """Re-queue every field not yet healed, with this attempt's rejection appended."""
    latest, best = state["latest"], state["verdicts"]
    failures = [
        dataclasses.replace(f, feedback=f.feedback + (_feedback_line(latest[f.field_name]),))
        for f in state["failures"]
        if best[f.field_name]["status"] != "healed"
    ]
    return {"failures": failures}


def _feedback_line(verdict: dict) -> str:
    return f"{verdict['selector'] or '(no selector)'} — {verdict['reason']}"


def _should_retry(state: HealState) -> str:
    done = all(v["status"] == "healed" for v in state["verdicts"].values())
    return END if done or state["attempt"] >= state["max_attempts"] else "retry"


def _build_heal_graph():
    g = StateGraph(HealState)
    g.add_node("propose", _propose)
    g.add_node("validate", _validate)
    g.add_node("retry", _retry)
    g.add_edge(START, "propose")
    g.add_edge("propose", "validate")
    g.add_conditional_edges("validate", _should_retry, ["retry", END])
    g.add_edge("retry", "propose")
    return g.compile()


HEAL_GRAPH = _build_heal_graph()


async def heal_cluster(
    provider,
    *,
    cleaned_html: str,
    specs: list,
    failures: list,
    rep_path: str,
    fields_by_name: dict,
    cluster_paths: list | None = None,
    paths_by_filename: dict | None = None,
    render_js: bool = False,
    examples: list | None = None,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> dict:
    """Run the heal loop on one cluster. Returns {proposals, attempts, model_ms}.

    ``proposals`` holds the best verdict per field, omitting fields the model never returned a
    selector for (there is nothing to review or accept).
    """
    final = await HEAL_GRAPH.ainvoke({
        "provider": provider,
        "cleaned_html": cleaned_html,
        "specs": specs,
        "failures": failures,
        "examples": examples or [],
        "rep_path": rep_path,
        "cluster_paths": cluster_paths or [],
        "fields_by_name": fields_by_name,
        "render_js": render_js,
        "paths_by_filename": paths_by_filename,
        "max_attempts": max_attempts,
    }, {"recursion_limit": 3 * max_attempts + 5})  # propose, validate, retry per attempt
    return {
        "proposals": {n: v for n, v in final["verdicts"].items() if v["selector"] is not None},
        "attempts": final["attempt"],
        "model_ms": final["model_ms"],
    }


# ---- batch level: detect → cluster → heal each ----


class DriftState(TypedDict, total=False):
    results: list
    fields: list
    provider: Any
    render_js: bool
    max_attempts: int
    field_rates: dict
    failing: list
    queue: list  # clusters still to heal
    clusters: Annotated[list, operator.add]  # healed cluster entries, appended per step


def _detect(state: DriftState) -> dict:
    rates = field_rates(state["results"], state["fields"])
    return {"field_rates": rates, "failing": failing_fields(rates)}


def _cluster(state: DriftState) -> dict:
    return {"queue": cluster_failures(state["results"], state["failing"])}


async def _heal_next(state: DriftState) -> dict:
    cl, *rest = state["queue"]
    rep = cl["representative"]
    entry = {"hash": cl["hash"], "size": cl["size"], "representative": rep["file"]}
    provider = state.get("provider")
    if provider is None:
        return {"queue": rest,
                "clusters": [entry | {"proposals": {}, "model": "unavailable", "attempts": 0}]}

    from spike.cleaner import clean_html

    specs, failures = _specs_and_failures(state["fields"], state["failing"], rep)
    healed = await heal_cluster(
        provider,
        cleaned_html=clean_html(
            Path(rep["path"]).read_text(encoding="utf-8", errors="replace")
        ),
        specs=specs,
        failures=failures,
        rep_path=rep["path"],
        fields_by_name={f["name"]: f for f in state["fields"]},
        cluster_paths=[f["path"] for f in cl["files"][1:]],
        # the anchor check needs to reach the page its value was captured on (§10 step 5)
        paths_by_filename={f["file"]: f["path"] for f in cl["files"]},
        render_js=state.get("render_js", False),
        max_attempts=state.get("max_attempts", DEFAULT_MAX_ATTEMPTS),
    )
    entry |= {"proposals": healed["proposals"], "model": provider.name,
              "attempts": healed["attempts"]}
    return {"queue": rest, "clusters": [entry]}


def _specs_and_failures(fields: list, failing: list, rep: dict) -> tuple[list, list]:
    """Spike FieldSpec + Failure lists for the provider, from config + the rep's statuses."""
    from spike.heal.provider import Failure, FieldSpec

    specs = [
        FieldSpec(name=f["name"], field_type=f.get("type") or "text",
                  old_selector=f.get("selector", ""))
        for f in fields
    ]
    failures = [
        Failure(
            field_name=name,
            dq_status=rep["field_status"].get(name, "empty"),
            extracted_value=(
                rep["data"].get(name) if isinstance(rep["data"].get(name), str) else None
            ),
        )
        for name in failing
    ]
    return specs, failures


def _build_drift_graph():
    g = StateGraph(DriftState)
    g.add_node("detect", _detect)
    g.add_node("cluster", _cluster)
    g.add_node("heal", _heal_next)
    g.add_edge(START, "detect")
    g.add_conditional_edges("detect", lambda s: "cluster" if s["failing"] else END,
                            ["cluster", END])
    g.add_edge("cluster", "heal")
    g.add_conditional_edges("heal", lambda s: "heal" if s["queue"] else END, ["heal", END])
    return g.compile()


DRIFT_GRAPH = _build_drift_graph()


async def run_heal(
    results: list,
    fields: list,
    provider,
    render_js: bool,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> dict:
    """Detect drift across a batch's results and heal every failing cluster."""
    final = await DRIFT_GRAPH.ainvoke(
        {
            "results": results,
            "fields": fields,
            "provider": provider,
            "render_js": render_js,
            "max_attempts": max_attempts,
            "clusters": [],
        },
        # one step per cluster, and a batch has at most one cluster per file; LangGraph's
        # default of 25 would abort any batch with more than ~22 distinct layouts
        {"recursion_limit": len(results) + 5},
    )
    if not final["failing"]:
        return {"triggered": False, "field_rates": final["field_rates"]}
    return {"triggered": True, "failing": final["failing"],
            "field_rates": final["field_rates"], "clusters": final["clusters"]}
