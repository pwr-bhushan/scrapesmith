# Plan: Presentable Repo (A) + Measured Heal Memory (B)

**Created:** 2026-09-04
**Branch:** `dev`
**Budget:** ~15h
**Decisions locked:** Python 3.12 upgrade first · A = metadata + nits + screenshots · B = Ollama-only bench

## Decisions confirmed 2026-09-04 (session 2)

Re-audited from source; prior findings hold. User chose:

1. **Python 3.12 upgrade first** — do Phase 0 before anything else.
2. **Install Postgres, capture 4 screenshots** — accept the ~2.5h. Postgres also un-skips
   14 tests and lets the heal *route* (not just `post_check`) run live.
3. **MIT license.**

### Audit deltas found this session (not in the original findings table)

- **README's test claim is only half wrong.** The `## Tests` section says "143 tests;
  DB/Redis/Playwright tests self-skip" — accurate (143 = collected). Only the `Docs & status`
  paragraph's "backend 143 tests passing" overstates. Fix that one line, not both.
- **`pytest` from the repo root yields 10 failures**, all `async def function and no async
  plugin installed`. Root pytest doesn't discover `backend/pyproject.toml`'s `asyncio_mode`.
  Passing from `backend/` (129/14). A reviewer who clones and types `pytest` sees red.
  Fix: root-level pytest config. Cheap, high presentability value.
- **README needs no rewrite** — targeted edits only. Phase A drops from ~3.5h to ~1.5h
  excluding screenshots; the slack goes to B.
- Confirmed no stubs anywhere: 0 `TODO`/`FIXME`/`NotImplementedError` in `app/`, `spike/`,
  `frontend/`. 21 routes, 9 components, all real. List-detection claim is real
  (`parser.py:41-50`, `scope == "list"`).

---

## 0. Audit findings that changed the premise

The task as written assumed a repo state that no longer holds. Verified against the working tree:

| Assumption | Reality |
|---|---|
| "README still says Status: planning" | **False.** Rewritten in `a4c49da` → `561c7d9` → `283d0ab`. Has tagline, features, quickstart, mermaid heal-loop diagram, stack table, honest limitations. `docs/{architecture,api,deployment}.md` exist (368 lines). |
| "no description or topics" | **True.** `gh repo view` → `description: ""`, `repositoryTopics: null`. |
| "Stack: Python 3.12" | **False.** Venv is **3.9.6**; `requires-python = ">=3.9"`; ruff `target-version = "py39"`. |
| "build an eval harness" | **Already exists.** `spike/bench.py` (`load_case`/`run_bench`/`compute_metrics`) + `spike/report.py` + `tests/test_bench.py`. Computes `anchor_correct_rate`, `resolve_but_wrong_rate`, `no_proposal_rate`, per-provider. |
| "what's stubbed" | **Nothing is stubbed in code.** Zero `TODO`/`FIXME`/`NotImplementedError` in `app/` or `spike/`. |

**The real gaps:**

1. **No model.** No `ollama` binary, no `ANTHROPIC_API_KEY`. `select_provider()` → `None` → heal returns `model: "unavailable"`. The heal loop has **never run live**. This is the deferred "GATE" that `todo.md:32-34` has tracked since Phase 0.
2. **One fixture.** `fixtures/drift/amazon_product/` — 957 bytes, 2 fields. `anchor_correct_rate` over 2 fields ∈ {0%, 50%, 100%}. Not a measurement.
3. **No bench entrypoint.** `run_bench()` is a library function nothing invokes.
4. **Doc drift:** README claims "143 tests passing" — actual is **129 passed, 14 skipped**.
5. **No LICENSE.**

**Two facts that shape B:**

- `app/skeleton.py::_node_repr` already builds a canonical, dynamic-attr-stripped tree string. `dom_skeleton_hash` throws it away into a SHA-256. **The similarity signal you want already exists one function call upstream of the hash** — B doesn't need a new DOM normalizer, it needs to stop discarding `_node_repr`'s output.
- The few-shot injection point is one f-string: `spike/heal/prompt.py::build_prompt`. No template engine in the way.

**Environment:** Python 3.12.4 ✅ installed · Node v25.8.1 ✅ · Redis ✅ running on 6379 · Postgres ❌ not running · Docker ❌ not installed · Ollama ❌ not installed.

Bench needs **only Playwright + Ollama** (no DB). Screenshots need the full stack (Postgres required).

---

## Phase 0 — Python 3.12 upgrade (~1.5h)

Do this first: it changes the venv every later phase runs in, and re-doing B's work under a new interpreter is waste.

**Steps**
1. `pyproject.toml`: `requires-python = ">=3.12"`, `[tool.ruff] target-version = "py312"`.
2. Rebuild: `python3.12 -m venv .venv && .venv/bin/pip install -e '.[dev]'` then `.venv/bin/playwright install chromium`.
3. Drop the `UP007`/`UP045` ruff ignores — their justification ("breaks SQLAlchemy `Mapped[]` on the pinned Python 3.9 runtime") evaporates on 3.12. Both rules are **auto-fixable**: `ruff check --fix .` rewrites the 44 `Mapped[Optional[X]]` sites to `Mapped[X | None]`. Mechanical, not manual churn.
4. Delete the stale 3.9 comment at `app/models.py:3`.
5. Run `.venv/bin/pytest` — expect 129 passed / 14 skipped, unchanged.
6. Update `.github/workflows/ci.yml` Python version.
7. Update README stack table + quickstart (`python3.9` → `python3.12`).

**Risk:** `asyncpg`/`lxml` wheels for 3.12 — both ship 3.12 wheels, low risk. If a build fails, pin up rather than reverting the interpreter.

**Exit:** suite green on 3.12, ruff clean, no `py39` string left in the repo.

---

## Phase A — Presentable (~3.5h)

### A1. Repo metadata (~15min)
```bash
gh repo edit --description "Self-healing HTML parser: click to pick fields in a rendered page; when markup drifts, an LLM rebuilds the selectors and proves the rebuild extracts the right value."
gh repo edit --add-topic web-scraping,html-parser,llm,self-healing,fastapi,playwright,python,nextjs,postgres,anchor-validation
```

### A2. Honesty fixes (~30min)
- README: `143 tests` → `129 passed, 14 skipped (integration tests self-skip without Postgres/Redis)`.
- Add `LICENSE` (MIT unless you prefer otherwise — **decision point**).
- Re-verify the three `docs/*.md` against the 3.12 change.

### A3. Screenshots / demo (~2.5h)
The product is visual and the README has no image — this is the largest presentability gap.

**Prerequisite:** Postgres must run. Docker isn't installed, so either `brew install postgresql@16 && brew services start postgresql@16` (~20min, README already documents this path) or install Docker Desktop. Redis is already up.

**Capture list** (4 stills > 1 GIF — cheaper, and they survive being viewed on a phone):
1. Click-to-pick — popover open over a rendered preview, selector ladder result visible
2. Canary parse — per-field DQ statuses (`ok`/`regex_fail`/…)
3. Batch results — per-field failure rates
4. **Heal review** — the value-first diff with the anchor check. *This is the money shot;* it's what makes the repo an AI-engineering repo rather than a scraper.

Store in `docs/img/`, embed after the README tagline.

> If Postgres setup fights back, ship A1+A2 and treat screenshots as the first thing to cut. Do not let it eat B's budget.

**Exit:** repo has description, topics, LICENSE, accurate test counts, 4 screenshots.

---

## Phase B0 — **NEW, BLOCKING: the heal prompt contains no DOM** (discovered during A3)

Capturing the screenshots ran the heal loop against a live model for the first time. Result on the
4-file drift cluster: both fields `still_broken`, proposals were the *old* selectors re-expressed as
XPath (`xpath=//h1[@class='product-title']`).

Root cause is not the model. `spike/cleaner.clean_html()` is named and documented as returning
"cleaned HTML" but calls `soup.get_text()` — it returns **plain text**. The representative failing
file reaches `build_prompt()` as:

```
Samsung Galaxy Book4 Pro — Product Listing
 Samsung Galaxy Book4 Pro
 ₹1,54,990
 Inclusive of all taxes
 4.4
 (302 ratings)
 In Stock
```

No tags, no classes, no ids. The prompt then asks for CSS/XPath selectors under a heading that says
"HTML (cleaned)". The task is impossible as posed; echoing the old selector is a rational response.

Second, smaller problem: `build_prompt`'s few-shot example is
`{"price": "css=.a-price-whole", "title": "css=.pdp-product-name"}` — real-looking Amazon-ish class
names. Any fixture whose drifted markup uses those names is measuring answer-leakage, not repair.
The eval corpus must avoid them (or the example must be neutralised).

**Consequence for the plan:** B1's baseline would be a measurement of this bug, and B2's heal memory
would be few-shot examples bolted onto a prompt with no DOM in it. B0 comes first.

### DECISION POINT 0 — what structure goes in the prompt
Tradeoff is fidelity vs. token budget vs. leakage.

| Option | What the model sees | Cost | Risk |
|---|---|---|---|
| (a) Tag+attr skeleton, text elided | `<h2 class="pdp-product-name">…</h2>` nesting, values truncated | small; scales to real pages | may elide the text needed to spot the right node |
| (b) Cleaned HTML, scripts/styles/comments stripped, attrs kept, text kept | closest to reality | large on real pages; needs the existing `token_cap` | truncation may cut the target |
| (c) Candidate-node shortlist | only the N nodes whose text/type plausibly matches, each with its path | smallest, most targeted | pre-selection does the model's job; if the shortlist misses, heal cannot recover |

Note `app/skeleton.py::_node_repr` already builds a canonical tag+attr tree string — option (a) is
mostly wiring an existing function into the prompt, and it is the same representation Decision Point
2 wants for DOM similarity. Reusing it makes B0 and B2 share one structural view.

**RESOLVED — chose (b).** The reuse argument for (a) was wrong: the two representations serve
different jobs and should not be shared. A *similarity signature* (Decision Point 2) wants text
elided, because text is the noise it clusters through. A *repair prompt* needs the text, because
after a redesign renames every class the value text is the only remaining evidence of which node
holds the price. Eliding it leaves the model matching on class names — exactly what drift broke.

Size on the drift fixture: raw 953 chars → (a) 311 → **(b) 594** → old `get_text()` 130. (b) costs
~2× (a) and stays well under the existing `token_cap`, which remains the escape hatch for real pages.

### B0 implementation — DONE

| Change | File |
|---|---|
| `soup.get_text()` → `soup.decode()`; drop `meta`/`link`/`noscript` with `script`/`style`; strip every attribute that cannot appear in a selector (keep `id`, `class`, `itemprop`, `role`, `aria-label`, `data-*`) | `spike/cleaner.py` |
| Neutralised the leaking few-shot example; added an explicit instruction to prefer the stability ladder and avoid positional paths | `spike/heal/prompt.py` |
| 4 regression tests: tags survive, selectable attrs survive, unselectable attrs dropped, text still survives | `tests/test_cleaner.py` |

All 15 pre-existing `test_cleaner.py` assertions passed unchanged — they only ever constrained
script/style/comment removal and text survival, never text-*only* output. Suite 145 → 149.

**Verified against the live model.** Same `ollama/qwen2.5-coder:7b`, same drift fixture, same two
fields:

| | before B0 | after B0 |
|---|---|---|
| title | `xpath=//h1[@class='product-title']` (the old broken selector) | `css=h2.pdp-product-name` → `Apple MacBook Pro 14-inch` |
| price | `xpath=//span[@class='price-value']` (the old broken selector) | `xpath=//span[@class='a-price-whole']` → `₹ 1,49,900` |

Caveat carried into B1: this fixture's class names are the ones the old prompt leaked. It proves the
cleaner fix, it does **not** count as a baseline data point — the corpus must use unrelated names.

### B0b — second blocker, found by the fix: `healed` was unreachable

With the cleaner fixed the model started proposing selectors that resolve to the right values, and
they all came back **`suspect · diverged`**. Not the model's fault either.

`post_check` step 5 compared the anchor to the value extracted from the *cluster representative*.
An anchor is an assertion about one page — "on `00_apple-macbook.html`, price reads ₹1,49,900". The
representative is whatever file heads the largest failing bucket, generally a different product. So
`anchor_ok` was False on every real batch, and since `status = "healed" if (anchor_ok is not False
and extra_ok)`, **`healed` was unreachable for any batch of distinct records**. It only ever passed
in `test_heal.py`, where both fixture files hold the same value.

Fix: the anchor records the filename it was captured from, and the check runs against *that* page
within the cluster.

| Change | File |
|---|---|
| Anchor gains `file`; picker stamps the page being viewed | `PickPopover.tsx`, `RenderFrame.tsx`, `lib/api.ts` |
| `_anchor_check` resolves on the anchor's page; `_resolve_at` extracted (also de-duplicates `_validate_others`) | `app/heal.py` |
| `paths_by_filename` passed from the cluster | `app/routes/heal.py` |
| Review shows `✓ value` / `✗ value` / `value · not in this cluster` instead of a bare value | `HealReview.tsx` |
| 3 tests: checked on its own page, still catches a wrong value, outside-cluster is None not False | `tests/test_heal.py` |

Filename, not index: it makes the anchor survive across crawls, which is the case that matters.

**Three-valued, deliberately.** `anchor_ok = None` means "this guard has nothing to say here", not
"passed". Within one crawl the page the operator picked on is by definition a page that still
parses, so it is never in the failing cluster and the anchor is never evaluable. The check earns its
keep on the **re-crawl**: same URLs, redesign now complete, the anchor's page is now drifted too and
lands in the cluster. Verified end to end — crawl 2 shows 100% failure, one 10-file cluster, and
both proposals `healed` with `✓ Apple MacBook Pro 14-inch` / `✓ ₹1,49,900`.

**Feeds Decision Point 3** (what scores as a successful heal): the eval corpus must be built as
before/after *pairs of the same page*, or the anchor is unevaluable and the harness can only score
the weaker DQ + cross-file signal.

---

## Phase B1 — Baseline measurement (~5h)

**Nothing about heal memory gets built until there is a number.** Baseline must be taken *after* B0,
otherwise it measures the cleaner bug rather than heal quality.

### B1.1 Ollama (~30min)
`brew install ollama && ollama serve`, then `ollama pull qwen2.5-coder:7b` (the `OllamaProvider.DEFAULT_MODEL`). Export `OLLAMA_HOST=http://localhost:11434` so `select_provider()` stops returning `None`.

### B1.2 Bench CLI (~45min)
`spike/bench.py` has no entrypoint. Add `backend/spike/__main__.py` — argparse over `--fixtures`, `--provider`, `--out`; calls the existing `load_case` → `run_bench` → `compute_metrics` → `render_table`/`write_artifacts`. No new logic, just wiring.

> Note: `resolve_selector` launches a fresh Chromium per call. 20 cases × 3 fields = 60 launches ≈ 1–2 min per bench run. Acceptable; don't optimize until it hurts.

### B1.3 Fixture corpus (~2.5h) — **DECISION POINT 1**

One fixture is not a corpus. Need ~15–20 cases.

| Option | Pros | Cons |
|---|---|---|
| **Synthetic mutation** — write a mutator applying labelled drift transforms (rename class, wrap in `div`, change tag, reorder siblings, strip `data-*`, move text into child) to real saved pages | Cheap, reproducible, scales instantly, and **labels drift type** → you can report heal rate *per drift class*, which is a far more interesting result than one scalar | Synthetic drift may be easier than real redesigns; a reviewer may discount it |
| **Real pairs via Wayback Machine** — pull before/after snapshots of real sites | Highest fidelity, unimpeachable | Slow (~10min/pair), messy HTML, anchors must be hand-labelled, licensing ambiguity |
| **Hybrid** — 5 real pairs anchoring credibility + 15 synthetic for volume and per-drift-type breakdown | Best of both; the real pairs validate that synthetic difficulty is calibrated | Most work |

**RESOLVED — chose synthetic mutation.**

B0b makes this close to forced: the anchor check only fires when the anchor's page is in the
failing cluster, so every case must be a before/after pair *of the same page*. A mutator gives that
by construction — `after.html` **is** `before.html` put through a labelled transform, so the anchor
value is guaranteed to still be present and still be correct. Hand-collected real pairs would need
that verified by hand, case by case.

The `drift_type` label is the real prize: it turns one scalar into a table that says *which kinds of
drift the model handles*, which is the interesting result and the axis B2's heal memory is supposed
to move.

| Piece | Where | Shape |
|---|---|---|
| Base pages | `backend/fixtures/base/*.html` | 4 hand-written realistic pages (product, article, job, event), 3 fields each |
| Transforms | `backend/spike/mutate.py` | `class_rename`, `tag_swap`, `wrapper_insert`, `attr_strip`, `combo` — BeautifulSoup, already a dep |
| Generator | `backend/fixtures/generate.py` | 4 bases × 5 transforms = **20 cases**, each written as `before.html` / `after.html` / `case.json` |
| Label | `case.json` → `drift_type` | new key; `load_case` and `BenchCase` gain the field |

Generated fixtures are **committed**, not generated at bench time — a reviewer can read them, and
the number can't move under you between runs. The generator is committed too, so it stays
reproducible. Honest-limitation line stays in the README: synthetic drift is a lower bound on
difficulty, not a stand-in for a real redesign.

### B1.4 Run baseline + write it down (~1h)
Run the bench, commit `artifacts/baseline.json` + `.md`. Record `anchor_correct_rate`, `resolve_but_wrong_rate`, `no_proposal_rate`, per-drift-type breakdown, latency.

**This closes the Phase 0 GATE that has been deferred since June.** Independent of B2, this is a shippable, portfolio-worthy artifact: *"local 7B heals X% of drift cases; here's the harness that proves it."*

**Exit:** a committed baseline number with a reproducible command.

---

## Phase B2 — Heal memory (~5h)

### B2.1 — **DECISION POINT 2: how to signature a DOM**

`_node_repr` already gives a canonical structural string. The question is what metric space to put it in.

| Option | How | Pros | Cons |
|---|---|---|---|
| **1. Shingled `_node_repr` + Jaccard** | Char n-grams over the existing tree string; MinHash if it ever needs scale | Zero new deps. Deterministic. Explainable ("shares 78% of structural 5-grams"). Reuses the *exact* normalization clustering already trusts | Char n-grams over a serialized tree are a crude structural proxy; order-sensitive; no semantics |
| **2. Root→leaf path sets + TF-IDF cosine** | Tokenize each root-to-leaf tag path (`html>body>div.product>span.price`), TF-IDF, cosine | Still dependency-light. **The tokens are essentially selectors** — retrieved neighbours are relevant to the actual generation task, not just "similar pages". Interpretable | Needs a corpus for IDF; ignores sibling order/depth nuance |
| **3. Neural embedding** | `nomic-embed-text` via the Ollama you just installed; cosine over vectors | Most recognizable as AI engineering. Semantic — relates `price`/`cost`/`amount` | Heaviest. **Embedding models truncate at ~512–8k tokens, so a real product page overflows and you embed a truncated prefix** — a correctness problem, not just cost. Non-deterministic across model versions. And for *structural* similarity a text embedding keys on words, not tree shape — arguably the wrong tool |

**Framing worth considering:** implement 1 or 2 as the retriever, then measure whether 3 beats it. An eval-driven *"we tested embeddings and n-grams won"* is a stronger signal than *"we used embeddings"* — it demonstrates the harness earns its keep. Your call.

**RESOLVED — chose 2, root→leaf paths + TF-IDF cosine.**

Deciding argument: the retrieved neighbour is used as a *few-shot example of a selector*, so the
similarity metric should live in the same space as the thing being generated. A root→leaf path
(`html>body>div.product>span.price`) is one token away from being a selector; two pages that share
those tokens are two pages where the same selector shape works. Char n-grams (option 1) would score
two pages as similar because they share `</div><div cl` — true, and irrelevant to the task.

Not option 3 for a correctness reason, not a cost one: embedding models truncate at a fixed token
budget, so a real product page gets embedded as a truncated prefix — the signature would describe
the page's `<head>` and nav rather than the region the field lives in.

Implementation: pure stdlib. `paths(html) -> list[str]` walking the soup; IDF computed over the
memory store itself (it *is* the corpus); cosine over `collections.Counter`. No scikit-learn — a
TF-IDF cosine over a few hundred short documents is about 20 lines and adding a 30MB dep to avoid
them is not a trade.

Deferred, not dropped: benchmarking `nomic-embed-text` against this once the harness exists. That
comparison is nearly free at that point and *"we tested embeddings and paths won"* is the stronger
claim. Only worth the hour if the paths retriever shows a real lift first — no point A/B-ing two
retrievers when neither helps.

### B2.2 — **DECISION POINT 3: k**
Options: fixed `k=1` / `k=3` / `k=5`, or **sweep k ∈ {0,1,3,5} and publish the curve**. The harness makes the sweep nearly free, and `k=0` *is* the baseline — the curve is the deliverable.

Watch the interaction: `clean_html` output already fills much of a 7B's context. Each few-shot example adds a chunk. There is a k where retrieval helps and a k where context pressure makes it worse — finding that inflection is the interesting result.

**RESOLVED — sweep k ∈ {0,1,3,5}, publish the curve.**

`k=0` is by definition the B1 baseline, so the sweep costs three extra runs, not four, and it is the
only version of this experiment that can produce a *negative* result worth reporting. B0 made the
prompt substantially larger (the DOM is actually in it now), so the context-pressure inflection is
no longer hypothetical — a fixed `k` would have reported a number without saying whether it sat on
the right side of it.

Bench gains `--k`; the CLI loops it. Cost is linear: 20 cases × 4 values of k at ~10s/call ≈ 15min
per full sweep against the local 7B. Fine unattended.

### B2.3 — **DECISION POINT 4: what scores as a successful heal**

The codebase already has `anchor_correct` (normalized value == anchor). Options:

| Option | Definition | Note |
|---|---|---|
| **a.** `anchor_correct` alone | Simple, already implemented | Ignores whether the full `post_check` gate would have accepted it |
| **b.** Two-tier: `anchor_correct` + reaches `status == "healed"` (not `suspect`) through `app/heal.py::post_check` | Measures what the *product* would actually ship, not what the model emitted | More wiring — bench currently bypasses `post_check` |
| **c.** (b) **+ treat a rise in `resolve_but_wrong_rate` as a regression even if `anchor_correct_rate` rises** | **Catches the dangerous outcome:** few-shot examples can make the model more confident and more wrong. A heal memory that lifts correctness 10pts while doubling confidently-wrong values is a net loss for a system whose entire pitch is "guarded, not trusted" | Strongly recommended given the project's thesis |

**RESOLVED — chose (c): tiered score + regression guard.**

Success = `anchor_correct` **and** `post_check` returns `status == "healed"`. Two rates get reported
side by side and neither is allowed to hide the other:

- `anchor_correct_rate` — the model got the right value.
- `healed_rate` — the right value *and* the product's own gate would have shipped it. This is the
  headline number, because it is the only one that describes what a user would actually get.
- `resolve_but_wrong_rate` — **guard.** A candidate that raises `healed_rate` while raising this is
  recorded as a regression, not an improvement. For a system whose pitch is "guarded, not trusted",
  a change that produces more confidently-wrong values is a net loss even if it also produces more
  right ones.

**Wiring (this lands in B1, not B2** — the baseline has to be measured on the same definition the
candidate will be, or the before/after comparison is meaningless):

- `run_bench` writes `after.html` to a temp file and calls `app.heal.post_check` with
  `rep_path=<that file>`, `cluster_paths=[]`, `paths_by_filename={"after.html": path}`.
- Each case's field carries `anchor: {"value": …, "file": "after.html"}` so the B0b anchor check
  actually fires rather than returning `None`. This makes the bench exercise the real §10 gate,
  including the bug B0b fixed.
- `BenchResult` gains `status`; `compute_metrics` gains `healed_rate` and `per_drift_type`.
- `compare_metrics(baseline, candidate)` — the guard itself — lands in **B2**, where it has a second
  run to compare against. One run cannot regress against itself.

### B2.4 Build + measure (~3h)
Store `(signature, healed_config, drift_type)` on successful heals; retrieve top-k on failure; inject into `build_prompt`; re-run the identical bench; write `artifacts/heal-memory.json`; add a before/after table to the README.

**Storage — decision: JSONL file** (`artifacts/heal_memory.jsonl`), not Postgres. The eval harness is
DB-free today; a Postgres table would mean the benchmark can't produce a number without a running
database, which is exactly the friction that stops a benchmark from being re-run. Promoting it to a
table is a migration away if heal memory ever earns its place in the product.

---

## Budget reality

| Phase | Est. |
|---|---|
| 0 — 3.12 upgrade | 1.5h |
| A — metadata + nits + screenshots | 3.5h |
| B1 — Ollama + CLI + corpus + **baseline** | 5h |
| B2 — heal memory + re-measure | 5h |
| **Total** | **15h** |

This consumes the budget exactly, which means it will overrun. **B2 is the at-risk phase.** If it spills, the honest stopping point is end of B1: a reproducible harness, a real fixture corpus, and the first live heal number this project has ever produced — with the heal-memory design documented as the next step. That is a complete story on its own; a half-built retriever is not.

Cut order if pressed: A3 screenshots → B2.2 k-sweep → B2 entirely.

---

## Key files

| File | Op | Why |
|---|---|---|
| `backend/pyproject.toml` | Modify | 3.12 bump, drop UP007/UP045 |
| `backend/app/models.py` | Modify | ruff autofix `Optional[X]` → `X \| None`; drop stale 3.9 comment |
| `README.md` | Modify | version, test count, screenshots, before/after table |
| `LICENSE` | Create | missing |
| `docs/img/*.png` | Create | 4 screenshots |
| `backend/spike/__main__.py` | Create | bench CLI entrypoint |
| `backend/fixtures/drift/*/` | Create | 15–20 case corpus |
| `backend/app/skeleton.py` | Modify | expose `_node_repr` for similarity (B2) |
| `backend/spike/heal/prompt.py` | Modify | few-shot injection (B2) |
| `backend/spike/bench.py` | Modify | drift_type + post_check-aware scoring (B2.3) |
| `artifacts/baseline.json` | Create | the number |

## Risks

| Risk | Mitigation |
|---|---|
| Postgres setup eats A3 | Timebox 30min; ship A1+A2 and defer screenshots |
| 7B model proposes garbage → baseline ≈ 0% | A near-zero baseline is still a valid, reportable finding; if it's *literally* 0 the fixtures are too hard — recalibrate mutation severity |
| Synthetic drift too easy → inflated baseline, no headroom for B2 | Per-drift-type breakdown exposes this immediately; add harder transforms |
| B2 improves `anchor_correct` but raises `resolve_but_wrong` | Decision Point 4 option (c) makes this a *tracked regression*, not a hidden one |
| 3.12 upgrade breaks a wheel | Pin forward, don't revert the interpreter |

## Multi-model note

`~/.claude/bin/codeagent-wrapper` and `~/.claude/.ccg/prompts/` are absent, so `/multi-plan`'s Codex/Gemini phases could not run. This plan was produced from direct source audit (built-in tool fallback). No `SESSION_ID` handoff is available for `/ccg:execute`.
