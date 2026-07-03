# Phase 0 — Heal Spike — Implementation Plan

**Status:** draft (Step 1 PLAN output) — awaiting answers to open questions before implementation
**Owner:** Bhushan
**Last updated:** 2026-06-08
**Parent design:** [`self-healing-parser.md`](./self-healing-parser.md) — Phase 0 row in §12, §10 heal contract, §8.1 selector ladder, §6 ConfigField/anchor, §13, §15

> **Scope:** de-risk the headline (LLM self-healing) *before* any UI/stack scaffolding. Runs standalone as a CLI/notebook. No FastAPI / Next.js / Postgres / Redis / arq.

---

## Requirements Restatement

Build the smallest rig that answers one question with data: **can an LLM rebuild broken selectors that extract the _right value_ (anchor-correct), and which model should we use?**

1. A **heal-provider interface** — `propose(cleaned_html, fields, failures) -> {field: {"selector": "css=…|xpath=…"}}`.
2. Two implementations: **`OllamaProvider`** (local, default) and **`CloudProvider`** (Anthropic Claude, opt-in escape hatch).
3. An **HTML cleaner** — strip scripts/styles/comments, collapse whitespace, token-cap with chunking hook.
4. **3–5 real before/after drift pairs**, each with per-field **anchor values** (known-correct value) — ground truth.
5. A **bench harness + metric**: for each pair × model, the **anchor-correct heal rate**.
6. A **report** (CLI table + JSON artifact).
7. A written **GATE decision** → plan §13 item 1.

## The Bench Metric (the heart of the spike)

For one field on one drift pair, the proposed selector is **anchor-correct** iff *all* hold:
1. **Parses** — valid CSS/XPath for the resolution engine.
2. **Resolves** — returns ≥1 node in the *drifted* (after) DOM.
3. **DQ-passes** — extracted text satisfies the field's DQ rules (§9).
4. **Anchor-matches** — extracted value `==` anchor, or normalized-equal (currency/number/whitespace/case per type).

```
anchor_correct_rate(model) = (# anchor-correct fields) / (# total fields across all pairs)
```

Also reported per model: resolve-but-wrong-value rate (the dangerous "DQ passes, value wrong" case from §10 step 5), parse-fail rate, latency, per-pair breakdown.

## Proposed Module Layout

```
backend/
  pyproject.toml                  # spike deps only; grows in Phase 0.5
  spike/
    __init__.py
    heal/
      provider.py                 # HealProvider ABC + dataclasses (FieldSpec, Failure, Proposal)
      ollama_provider.py          # OllamaProvider (httpx → localhost:11434)
      cloud_provider.py           # CloudProvider (anthropic SDK, claude model)
      prompt.py                   # prompt builder (§10 sketch) — shared by both
    cleaner.py                    # clean_html() + token estimate + chunk hook
    resolve.py                    # resolve_selector(html, "css=…|xpath=…") -> [values]; normalize()
    dq.py                         # minimal DQ subset reused later (ok|empty|regex_fail|type_fail|range_fail)
    bench.py                      # harness: load fixtures × providers → metric → report
    report.py                     # render CLI table + write JSON/markdown artifact
  fixtures/
    drift/
      <case>/
        before.html               # markup the original selectors were built on
        after.html                # drifted markup the heal must target
        case.json                 # fields[], old selectors, DQ rules, per-field anchor value
  tests/
    test_cleaner.py
    test_resolve.py
    test_dq.py
    test_provider_contract.py     # ABC contract + a FakeProvider (no network)
    test_bench.py                 # metric math on a synthetic fixture w/ FakeProvider
  artifacts/
    phase0_report.{md,json}       # generated
```

`fixtures/drift/<case>/case.json` shape:
```json
{
  "host": "amazon.in", "page_type": "product_listing",
  "fields": [
    {"name": "price", "type": "currency",
     "old_selector": "css=[data-price-amount]",
     "dq": {"required": true, "regex": "[₹$€]\\s*[\\d,]+", "parses_as": "number"},
     "anchor": "₹1,49,900"}
  ]
}
```

## Selector Resolution Engine — decision needed (Q4)

Anchor-correctness must reflect *real* extraction. The design makes **Playwright the source of truth**. **Recommendation:** use **Playwright sync against `file://`** in `resolve.py` for the spike too — it's the real engine, supports both `css=`/`xpath=` via `locator()`, and avoids a CSS-engine mismatch between spike and product. Lighter alternatives (`parsel`/`lxml`) are faster but would let the spike pass selectors the real product later rejects, undermining the gate.

## TDD Order (tests first — workflow Step 2)

1. `test_cleaner.py` — scripts/styles/comments removed, text/anchor values survive, ₹ glyph preserved, token cap respected.
2. `test_resolve.py` — `css=`/`xpath=` resolve on a fixture; `normalize()` makes `"₹1,49,900"` == `" ₹ 1,49,900 "`; non-resolving selector → `[]`.
3. `test_dq.py` — each status reachable.
4. `test_provider_contract.py` — `FakeProvider` returns canned selectors; ABC enforces signature; bad output (missing key, non-prefixed selector) rejected/normalized.
5. `test_bench.py` — with `FakeProvider` whose answer is known, metric math is exact (e.g. 1 correct of 2 → 0.5). **No live model in unit tests.**

Live-model runs (Ollama/cloud) are the **bench execution**, not unit tests — gated behind env (`OLLAMA_HOST`, `ANTHROPIC_API_KEY`), skipped in CI.

## Dependencies (spike only)

`httpx` (Ollama REST), `anthropic` (cloud), `playwright` + `playwright install chromium` (resolution), `beautifulsoup4` + `lxml` (cleaner), `pytest`. Toolchain: `backend/.venv`, always invoked as `backend/.venv/bin/python` / `backend/.venv/bin/pytest` (per lessons.md).

## GATE Criteria (proposed — confirm in Q5)

- **GO** if a single model achieves **≥ 80% anchor-correct** across all pairs **and** **resolve-but-wrong-value ≤ 10%**.
- **CONDITIONAL GO** (cloud-only) if no local model clears 80% but cloud does → ship cloud as default, keep Ollama behind toggle.
- **NO-GO / re-architect** if even cloud is < 60% anchor-correct → §10 contract needs rework before building UI.
- Decision + chosen model + measured numbers written back to **plan §13 item 1** and a Review note in `todo.md`.

## Risks

| Risk | Sev | Mitigation |
|---|---|---|
| No real drift pairs available → spike tests nothing real | **HIGH** | Q1 — must source real pairs; synthetic-only weakens the gate |
| Ollama not installed / no GPU → local bench can't run | **HIGH** | Q2 — install + pull models, or run cloud-first and defer local |
| "DQ passes but wrong value" not caught | MED | the anchor-match step *is* the metric; explicitly reported |
| Playwright `file://` + blocked assets differ from real render | LOW | assets irrelevant to selector resolution; acceptable for spike |
| Token cap truncates the element the heal needs | MED | chunk hook + log when representative HTML is truncated |

## Open Questions (need answers before writing code)

1. **Drift pairs source** — where do the 3–5 real before/after pairs come from? (You provide saved HTML / I scrape-and-save public sites / start with 1 real + synthetic variants?) **#1 blocker.**
2. **Ollama** — install locally now and `ollama pull qwen2.5-coder:7b llama3.1:8b`? Or run the bench cloud-first and add local later? (Not currently installed.)
3. **Cloud provider/model** — Anthropic Claude. Which model — `claude-opus-4-8` or cheaper `claude-haiku-4-5` for iteration? Is `ANTHROPIC_API_KEY` in env?
4. **Resolution engine** — Playwright sync (recommended, matches product) vs lighter `parsel`/`lxml` for spike speed?
5. **GATE numbers** — accept 80% anchor-correct / ≤10% wrong-value, or set your own bar?

## Estimated Complexity: MEDIUM

Small code surface, but the bench metric and real fixtures are fiddly. Most effort is sourcing/labeling real drift pairs (Q1), not code.

---

## Decisions Log

Answered 2026-06-16 (resume session, before Step 2):

1. **Drift pairs** — **1 real + synthetic variants.** Start from one real page; hand-mutate markup (class renames, tag swaps, reordering) to simulate drift. Synthetic, so the GATE is directional for now; revisit with real pairs when available.
2. **Ollama** — **install + pull models now** (`qwen2.5-coder:7b`, `llama3.1:8b`) so the bench includes local from day one.
3. **Cloud model** — **Haiku (`claude-haiku-4-5`) for now, kept configurable** — model id lives in config/env, not hardcoded, so it's swappable to Sonnet/Opus.
4. **Resolution engine** — **Playwright sync against `file://`** (recommended; matches product source-of-truth).
5. **GATE** — **≥80% anchor-correct AND ≤10% resolve-but-wrong-value** for GO (as proposed).

Implications for Step 2: cloud model id must be a config value (Q3); collect/generate the 1-real+synthetic fixture set as part of fixtures (Q1).

---

## Step 6 — Fix Plan (post-review, 2026-06-16)

Review (python-review + ponytail-review) found the core metric math correct but flagged two metric-*classification* gaps that would flatter the GATE numbers, plus two safe mechanical fixes. Decisions below align the metric with this plan's already-stated intent (§"The Bench Metric" + §10 step 5), so they are correctness fixes, not new design choices.

**To fix (Step 7):**
1. **H1 — `resolve_but_wrong` must count every wrong resolution, not only DQ-passing ones.** A selector that resolves to a DQ-*failing* wrong value currently falls into a residual bucket and is uncounted. Set `resolve_but_wrong = (resolved_values non-empty) AND (not anchor_correct)` — independent of `dq_status`. This is the "DQ passes but wrong" headline risk from §10 step 5, widened to "resolves but wrong" so the ≤10% gate isn't gamed. The DQ-pass-but-wrong subset can still be reported separately if cheap, but the gate denominator uses the wider definition.
2. **H2 — rename `parse_fail_rate` → `no_proposal_rate`.** It counts missing/rejected proposals (`proposed_selector is None`), not Playwright parse failures. Rename to match reality; true parse-vs-resolve-nothing disambiguation is out of scope for the spike (Playwright swallows both to `[]`). Note this in the GATE table legend.
3. **M1 — `normalize()` number branch must collapse internal whitespace** like the currency/text branches: `re.sub(r"\s+", "", s.replace(",", ""))`. One-line metric-correctness fix.
4. **L1 — add one ~10-line smoke test for `report.py`** (`render_table`/`write_artifacts` on empty input → non-empty string + both files exist + JSON round-trips). It produces the GATE deliverable artifact, so a cheap guard is justified even for a spike.
5. **L5 / ponytail nits** — move `import re` to module top in `cleaner.py`; drop the placeholder-less `f` prefix in `report.py`. Trivial.

**Deferred (note only, no code change):** L2 (`Optional[str]` vs `str | None` under 3.9 — safe via `from __future__ import annotations`), L3 (prod sandboxing of attacker HTML into Playwright), L4 (prompt-injection hardening). These are production concerns; the spike measures the engine, not the threat model. Record L3/L4 as a one-line caveat in the eventual GATE write-up (§13).

---

## GATE Execution — Deferred to end-of-MVP (decided 2026-06-18)

The spike is code-complete and committed (`86ba558`). Running the live bench is the **only** remaining Phase 0 work, and it's blocked purely on env setup (`ANTHROPIC_API_KEY` unset; Ollama not installed, ~10 GB pulls) — not on code. `bench.py` is a self-contained script behind a clean provider interface; **nothing downstream depends on running it**. The GATE is a go/no-go *decision*, not a code dependency.

**Decision:** defer the live bench + GATE decision to the end of the MVP (built alongside whole-app end-to-end testing), and build forward through Phase 0.5 → 5 now. Plug in the key + Ollama at that point, run `bench.py` across providers, and write the go/no-go + model choice to plan §13 + todo.md Review.

**Risk accepted:** if the GATE later fails (local model can't produce generalizing selectors, §15 HIGH risk), Phase 6 heal may need re-architecture — but the cloud provider is a working escape hatch, and Phases 0.5–5 (skeleton, upload, picker, parser, batch) are independent of the model choice. Low blast radius.
