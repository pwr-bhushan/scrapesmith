# Scrapesmith — Todo

Tracks active phases from [`.claude/plans/self-healing-parser.md`](../plans/self-healing-parser.md) (v2, revised after critique).

## Phase 0 — Heal spike (de-risk the headline) ← DO FIRST

### Step 1 — PLAN ✅ (2026-06-08)
- [x] Phase 0 plan written to `.claude/plans/phase-0-heal-spike.md`
- [x] Decisions log answered (2026-06-16): drift pairs, Ollama, cloud model (haiku configurable), resolution engine (Playwright), GATE

### Step 2 — TESTS ✅ (2026-06-16)
- [x] `backend/.venv` created; deps installed (httpx, anthropic, playwright, beautifulsoup4, lxml, pytest)
- [x] `backend/pyproject.toml` scaffolded
- [x] Package skeleton: `spike/__init__.py`, `cleaner.py`, `resolve.py`, `dq.py`, `bench.py`, `report.py`, `heal/provider.py`, `heal/ollama_provider.py`, `heal/cloud_provider.py`, `heal/prompt.py`
- [x] Synthetic fixture: `fixtures/drift/amazon_product/{before,after}.html` + `case.json`
- [x] 5 test files written (73 tests): `test_cleaner.py`, `test_resolve.py`, `test_dq.py`, `test_provider_contract.py`, `test_bench.py`
- [x] Tests verified RED: 61 FAILED (NotImplementedError), 6 PASSED (ABC introspection + FakeProvider), 6 SKIPPED (Playwright — SKIP_PLAYWRIGHT=1)

### Step 3 — IMPLEMENT ✅ (2026-06-16)
- [x] Implement `clean_html()` in `cleaner.py`
- [x] Implement `resolve_selector()` + `normalize()` in `resolve.py`
- [x] Implement `check_dq()` in `dq.py`
- [x] Implement `validate_proposal()` in `heal/provider.py`
- [x] Implement `compute_metrics()` + `load_case()` + `run_bench()` in `bench.py`
- [x] Implement `OllamaProvider.propose()` and `CloudProvider.propose()`
- [x] Heal provider interface (heal/provider.py)
- [x] HTML cleaner (cleaner.py)
- [x] Bench harness + metric (bench.py, unit-tested)

**Phase 0 CODE COMPLETE:** All spike modules implemented and unit-tested (74 passed, 6 skipped, 0 failed, 64% coverage). Remaining work is live bench execution + GATE decision (requires Ollama installed, models pulled, `playwright install chromium`, ANTHROPIC_API_KEY set).

### Later — DEFERRED to end-of-MVP (decided 2026-06-18, see phase-0 plan §"GATE Execution — Deferred")
- [ ] Collect 3–5 real before/after drift HTML pairs (with known correct values = anchors) — PARTIAL: 1 synthetic case built; real pairs still needed
- [ ] **GATE:** go/no-go + model choice written back to plan §13 — requires live bench (ANTHROPIC_API_KEY + Ollama); run during whole-app E2E testing, not now

## Phase 0.5 — Skeleton ✅ (2026-06-18) — plan: `.claude/plans/phase-0.5-skeleton.md`

- [x] FastAPI (async) boots with `/health` → 200 (ASGI test + real uvicorn curl)
- [x] Postgres + first Alembic migration (`domain`, `config_version`, `upload_batch`, `upload_file`, `parse_result`, `job`) — applied, circular FK broken via `use_alter`
- [x] Redis + arq worker smoke test (no-op job round-trips)
- [x] Playwright pool smoke test (renders `before.html` headless)
- [x] Next.js app boots with shared typed API client (`getHealth()`); build + tsc green
- [x] CI: ruff + pytest (pg/redis service containers) + frontend tsc

## Phase 1 — Upload + Playwright render ✅ (2026-06-18) — plan: `.claude/plans/phase-1-upload-render.md`

- [x] `POST /upload` accepts single `.html` / `.gz` / `.zip` (zip-bomb + size + count caps in `app/upload.py`)
- [x] Files persisted to `./uploads/{batch_id}/{index}_{name}`; `domain` get-or-create + `upload_batch` + `upload_file` rows
- [x] `dom_skeleton_hash` per file (`app/skeleton.py`, §411 — dynamic attrs stripped, stable class/role kept)
- [x] Frontend upload screen (5.1) with JS-render toggle (`components/UploadForm.tsx`)
- [x] Render file N in isolated egress-blocked Playwright context; sanitized + CSP + hover overlay; sandboxed iframe; Prev/Next (`app/render.py::render_snapshot`, `components/RenderFrame.tsx`)
- Deferred to Phase 2: click-to-select, selector ladder, list detection, `/pick/validate`, popover

## Phase 2 — Click-to-select + stability ladder ✅ (2026-06-18) — plan: `.claude/plans/phase-2-click-select.md`

- [x] Selection JS in the overlay (our script only, existing strict CSP): click → descriptor + list detection → postMessage
- [x] Selector stability ladder (`app/selector.py`, §8.1): id → data-* → itemprop/role → stable class under landmark → `:nth-of-type` fallback
- [x] `/pick/validate` round-trips candidates through Playwright `locator()` on the raw file; first unique wins (`app/pick.py`, `routes/pick.py`)
- [x] List detection (§8.2): overlay finds nearest ancestor with ≥3 similar children; parent-relative selector; count ≥2
- [x] Side panel adds field on click (manual name); save/get config v1 (`routes/config.py`, `PickPopover`, `FieldPanel`)
- Deferred: type auto-detect/presets + ✨ LLM (Phase 3); DQ/anchors (Phase 4)

## Phase 3 — Inference + presets ✅ (2026-06-18) — plan: `.claude/plans/phase-3-inference.md`

- [x] `/infer`: structured (itemprop/data-*) → text regex → label-proximity cascade (`app/infer.py`); JSON-LD value-match deferred
- [x] Field type preset library (`app/presets.py`): title/price/discount_pct/rating/review_count/availability/image/url/date/description/location + custom, each with regex + default DQ + synonyms
- [x] Popover UI (5.3): "Looks like TYPE (conf%)" + Change dropdown + value; field carries type + preset dq
- [x] ✨ "Ask AI" opt-in LLM classifier — plumbed; honest `llm_unavailable` without ANTHROPIC_API_KEY (never automatic)

## Phase 4 — Parser + DQ + anchors ✅ (2026-06-18) — plan: `.claude/plans/phase-4-parser-dq.md`

- [x] Generic parser runs a config in the browser context → `parse_result` (`app/parser.py`)
- [x] DQ engine `ok|empty|regex_fail|type_fail|range_fail|out_of_scope` (`app/dq.py`, ported from spike + min/max_len + url + out_of_scope)
- [x] Capture field **anchor** (value + descriptor fingerprint) at Confirm; stored in config field
- [x] Canary panel (5.5): `POST /parse/canary` runs config on one file, stores parse_result, returns per-field value/DQ/anchor_ok (`CanaryPanel`); Re-pick = same picker screen

## Phase 5 — Async batch + per-field rates + export ✅ (2026-06-18) — plan: `.claude/plans/phase-5-batch-export.md`

- [x] `POST /parse/batch` enqueues an arq job; `app/batch_parse.py::run_batch` parses each file, stores parse_result, updates job.progress
- [x] `GET /jobs/{id}` + `GET /jobs/{id}/stream` (SSE) progress
- [x] Per-field failure rate + item-level flagged_ratio (`app/aggregate.py`)
- [x] Batch results screen (5.8) with progress bar (`BatchResults`)
- [x] CSV (one row per list item, `__file`/`__item_index`) + nested JSON export (`app/export.py`, `/batch/{id}/export.csv|.json`)

## Phase 6 — Heal (cluster → propose → value-first review) ✅ (2026-06-18) — plan: `.claude/plans/phase-6-heal.md`

- [x] Per-field drift trigger (§9): `failing_fields` at ≥30% (`app/heal.py`)
- [x] Cluster failing files by `dom_skeleton_hash`; representative = centroid (`cluster_failures`)
- [x] Heal each cluster via provider (reuses spike Cloud/Ollama providers; `select_provider` gated); anchor enforced by post-check not prompt
- [x] Post-check (§10 steps 1–6): valid prefix → resolves → DQ → not-too-positional → **anchor match** → 2 more cluster files → healed|suspect|still_broken
- [x] Drift UI (5.6) + value-first review (5.7) with suspect flagging (`HealReview`); `/heal/propose` + `/heal/accept` (new config_version, created_by=llm-heal)
- [x] Anti-loop: cluster-once per hash; suspect/still_broken never auto-applied. Live model wiring = same deferred GATE dependency (post-check tested with FakeProvider).

## Phase 7 — Versioning ✅ (2026-06-18) — plan: inline (small)

- [x] Version assignment under `pg_advisory_xact_lock(hashtext(domain_id))` in `create_config_version` (§11); concurrency test proves 1,2 no collision
- [x] Version list per domain (`GET /domains/{id}/versions`) + diff view (`app/versioning.py`, `GET /domains/{id}/diff?a&b`)
- [x] Pin batch to specific version (`POST /batch/{id}/pin`); `effective_config_version` (pinned else latest) now drives parse/canary/results/heal
- [x] Frontend `VersionPanel`: list, diff last two, pin

## Phase 8 — Advanced mode polish ✅ (2026-06-18)

- [x] Advanced toggle (`AdvancedPanel` collapsible)
- [x] Editable selectors/types/DQ via raw JSON editor
- [x] Raw JSON config editor with client validation (parse + shape check) → saveConfig
- [x] Custom selector flow: `POST /selector/check` resolves a hand-written selector; custom DQ edited inline in the JSON

---

## Phase A/B — Presentable + measured heal loop (2026-09-04 →) — plan: [`presentable-and-heal-memory.md`](../plans/presentable-and-heal-memory.md)

### A — Presentable ✅
- [x] Python 3.12 upgrade; MIT LICENSE; repo metadata
- [x] Honesty pass on README (no measured heal rate, one-case corpus, anchor scope)
- [x] 4 screenshots captured against the real UI + a live local 7B (two-crawl demo corpus)

### B0 — Blockers found while doing A ✅
- [x] `clean_html` returned plain text — the heal prompt contained no DOM at all. Now serializes
      the soup with only selectable attributes kept.
- [x] Answer leakage removed from the prompt's format example.
- [x] **B0b:** `post_check` compared the anchor to the cluster representative (a different page),
      so `healed` was unreachable on any batch of distinct records. Anchors now record their source
      file and are checked on it; `None` when inapplicable, surfaced in the UI as "not in this cluster".

### B1 — Baseline measurement
- [x] Ollama + `qwen2.5-coder:7b` running
- [x] **Decisions 1–4 resolved** (synthetic mutation / paths+TF-IDF / sweep k / tiered + guard) and written to the plan
- [x] `spike/mutate.py` — 5 labelled drift transforms, self-checked
- [x] `fixtures/base/*` — 4 base pages × 3 fields; `fixtures/generate.py` → **20 generated cases, 46 drifted fields**
- [x] `spike/__main__.py` — bench CLI (`python -m spike --fixtures … --provider … --out …`)
- [x] Tiered scoring wired: `run_bench` runs the real `app.heal.post_check`; `healed_rate` +
      `per_drift_type` added to `compute_metrics`
- [x] Tests: `test_mutate.py` + new `test_bench.py` classes — 173 pass, ruff clean
- [x] Full baseline run, `artifacts/` committed (gitignore exception), number in the README

**Baseline result — 21 cases, 48 fields, `ollama/qwen2.5-coder:7b`:**

| metric | value |
|---|---|
| `healed_rate` (headline) | **95.83%** (46/48) |
| `anchor_correct_rate` | 95.83% |
| `resolve_but_wrong_rate` | 0.00% |
| `no_proposal_rate` | 0.00% |

Per drift type: `attr_strip` 100% (n=7), `class_rename` 100% (n=12), `tag_swap` 100% (n=10),
`combo` 91.7% (n=12), `wrapper_insert` 80% (n=5). Only 2 failures, both `still_broken`/`empty`:
`article__combo/headline`, `event__wrapper_insert/venue`.

### B1b — Harden the corpus (baseline is saturated)
**Why:** every anchor value is globally unique in its base page, so selector repair degenerates into
string search. 4.17% of headroom cannot show lift from heal memory, and `resolve_but_wrong_rate` is
structurally pinned at 0 — there is no wrong-but-plausible value in the page to pick.
**Decided 2026-09-05:** add decoys to the base pages (plan §B1b).

- [x] Rewrite `fixtures/base/*.html` with DQ-passing competitors per field, in sibling/aside
      containers only — never inside the field's own container, or no correct selector exists
- [x] Tighten `generate.py`: old selector must resolve to exactly **1** element on `before.html`
- [x] Regenerate the corpus — same 20 cases / 46 fields, only the difficulty moved
- [x] `test_every_field_has_a_wrong_answer_available` — guards the corpus against re-flattening
- [x] Re-run the baseline; soft vs hard reported side by side
- [x] **Gate met:** `resolve_but_wrong_rate` 0.00% → **2.08%**

| metric | soft | hard |
|---|---|---|
| `healed_rate` | 95.83% | **91.67%** |
| `resolve_but_wrong_rate` | 0.00% *(pinned)* | **2.08%** *(live)* |

`product__combo/price` → proposed `div.c0929-price` → resolved `₹2,999` (the header promo strip),
DQ `ok`, **anchor check caught it** → `suspect`. The §10 thesis, demonstrated on the bench.

⚠️ **CORRECTED 2026-09-05 (see B2.0).** The 95.83 → 91.67 drop is *within run-to-run noise* — four
runs of the identical hard-corpus config gave 91.67 / 91.67 / 97.92 / 97.92. The decoys' effect on
`healed_rate` is **not** established. What holds structurally is that `resolve_but_wrong_rate`
became *reachable*, which follows from the corpus containing wrong-but-valid values by
construction. Both rate values above are ±3pp.

### B2 — Heal memory — plan written 2026-09-05, decisions 5–7 resolved (plan §B2.0–B2.4)

**B2.0 — BLOCKING: make the bench reproducible**
- [x] `OllamaProvider` sends `options: {temperature: 0, seed: 1234, num_ctx: 8192}` — remedy
      pre-validated 2026-09-05: 4 identical calls gave 3 distinct outputs before vs 1 pinned
- [x] Verify `num_ctx` is large enough that the cleaned HTML is not already being truncated —
      **done 2026-09-05: it is.** The corpus's largest prompt (`product__combo`) is 1244 tokens
      against Ollama 0.33.2's 4096 default, so B1's numbers were never truncated and there is
      ~2850 tokens of headroom for few-shot examples. Still set explicitly so an Ollama
      upgrade cannot silently move it.
- [x] **Exit gate PASSED 2026-09-05:** two consecutive `k=0` runs produced byte-identical
      proposals for **48/48** fields, and identical metrics to 4dp.
- [x] Re-run the baseline deterministically. **Pinned baseline = `healed_rate` 95.83% (46/48),
      `anchor_correct_rate` 95.83%, `resolve_but_wrong_rate` 2.08% (1/48), `no_proposal_rate` 0%.**
      Note this landed at the *top* of the sampled 91.7–97.9 range, not the bottom — the earlier
      prediction that greedy decoding would lock in the `div.c0929-price` decoy and depress the
      number was wrong. That decoy is still the single `resolve_but_wrong` field; it just was not
      accompanied by the other losses sampling had been producing.

**B2.1 — signature + retriever** (`spike/memory.py`, stdlib only)
- [x] `paths()` — tag path + attribute **names**, classes excluded (they are what `class_rename`
      destroys, so class tokens do not survive the drift the retriever must see through)
- [x] `idf()` / `cosine()` / `retrieve(sig, store, k, exclude)` — `exclude` applied *before*
      ranking, so excluding a self-match cannot silently return k−1 neighbours

**B2.2 — memory store** (`artifacts/heal_memory.jsonl`)
- [x] Entry = case/host/page_type/drift_type + field, old→healed selector, signature
- [x] **No anchor values, no raw HTML** — enforced by test over the whole corpus. The leak scan
      runs over string fields + signature *keys*; signature values are element counts and one
      corpus anchor is the single character `"7"`, so a raw substring scan false-positives
      whenever a page has seven of some tag.
- [x] Populate only from `anchor_correct AND status == "healed"` on a k=0 run — never ground truth.
      The seeded store holds **46 entries**, exactly the 46 fields that healed at k=0.
- [x] Both partitions: LOO (same case excluded) and LOBO (same base page excluded)

**B2.3 — prompt injection**
- [x] `build_prompt(..., examples=())`; `propose(..., examples=())` on the ABC and both providers
- [x] **k=0 prompt stays byte-identical** — locked by `tests/golden/prompt_k0.txt`, captured from
      HEAD before `prompt.py` was touched. `run_bench` also calls `propose` positionally when
      there is nothing to retrieve, so the k=0 arm matches B1 at the call site too.
- [x] Log retrieved neighbours per case — see `neighbours.md` (reconstructed post-hoc; `retrieve()`
      is a pure function of the recorded store + case, so this is exact, not an approximation)

**B2.4 — sweep + compare**
- [x] `--k`, `--partition {loo,lobo}`, `--memory`, `--save-memory`; 2 k=0 gate runs + 6 sweep arms
- [x] `compare_metrics(baseline, candidate)` → `regression: True` if `resolve_but_wrong_rate` rises
      **or** `healed_rate` falls
- [x] README k-curve for both partitions + the power limit stated (n=48 resolves ~2pp)
- [x] `write_artifacts(..., arm=...)` records provider/k/partition/memory_entries — without it a
      k=5 report is byte-indistinguishable on disk from a k=0 one
- [x] Committed `backend/artifacts/phase0_report.{json,md}` regenerated as the pinned k=0 baseline
      (95.83%, was the older sampled 91.67% run). The rerun reproduced **48/48** selectors identical
      to the gate run — a third determinism confirmation, not just a refresh.

**B2 result — 6 arms + 2 gate runs, 2026-09-05**

| arm | `healed` | `wrong` | Δ healed | Δ wrong | regression |
|---|---|---|---|---|---|
| k=0 baseline | 95.83% | 2.08% | — | — | — |
| k=1 loo | 95.83% | 2.08% | +0.00 | +0.00 | False |
| k=3 loo | **100.00%** | 0.00% | +4.17 | −2.08 | False |
| k=5 loo | 97.92% | 0.00% | +2.08 | −2.08 | False |
| k=1 lobo | 97.92% | 0.00% | +2.08 | −2.08 | False |
| k=3 lobo | 97.92% | 0.00% | +2.08 | −2.08 | False |
| k=5 lobo | 97.92% | 0.00% | +2.08 | −2.08 | False |

The whole LOBO effect is one field — `product__combo`/`price`, the promo-strip decoy. k=0 answers
`css=div.c0929-price` (₹2,999, passes the price regex, DQ says `ok`); every k>0 lobo arm answers
`css=.cb8af-value` and gets it right. The other baseline failure, `event__tag_swap`/`venue`, does
not resolve at all and no value of k rescues it. n=48 means one field *is* 2.08pp, so this is
reported as "the guard metric went to zero, consistently, at every k", not as a 2pp heal-rate win.

LOO is degenerate and measured rather than assumed: 20/21 (95.2%) of its k=1 neighbours are another
drift variant of the *same base page*. LOBO is 0/N by construction. LOO is the ceiling, LOBO the claim.

### B2.5 — code-review fixes (`ponytail:ponytail-review`, 2026-09-05) — plan §B2.5

Four HIGH findings. Every one was re-measured against the real corpus before being accepted;
one did not survive that.

- [x] **H2 — `retrieve()` weighted idf by the whole store, including partition-excluded entries.**
      Confirmed and blocking: LOBO top-k moved on **5/21** cases at k=1 and **10/21** at k=5 between
      `idf(store)` and `idf(pool)`. Under LOBO the held-out page was steering the ranking it had
      been excluded from. One-word fix, but it invalidates the first sweep → re-run.
- [x] **H4 — leakage claim DISCONFIRMED, false disclaimer fixed anyway.** Checked whether any
      retrieved example carried the exact `healed_selector` the case under test needed:
      **0/46 fields**, every arm, both partitions — per-case class renames mean a sibling's answer
      is never this page's answer. What *was* real: the block said "(reference only — these are
      different pages)", which is false under LOO by construction. Deleted rather than made
      partition-aware.
- [x] **H3 — `k` counts entries, not pages.** Confirmed: distinct source pages per prompt are
      1.00 at k=1, 1.38–1.57 at k=3, 2.38–2.57 at k=5. Documented, not "fixed" — one entry per
      healed field is what the store *is*, and deduping by page would be a different experiment.
      This is also the explanation for the flat LOBO curve, so it is a finding.
- [x] **H1 — `--save-memory` had no guard.** `save_store` overwrites, so `--k 5 --save-memory` or
      `--case X --save-memory` silently replaced the seeded store and every later arm read it.
      Now `parser.error`s on both.
- [x] M1 `bench.py` comments reworded — the k=0 arm shares B1's *code path*, not its configuration
- [x] M2 `BenchResult.n_examples` — records examples delivered, not the k requested
- [x] L1 `save_store` docstring said "appendable"; it overwrites
- [x] L2 `cosine` OOV weight was 1.0, the idf *floor*, for the most discriminative tokens
- [x] L3 `_base_page` grouping is name-shaped — `ponytail:` comment names the ceiling
- [x] L4 `_render_examples` `.get(..., "?")` so a stale jsonl line degrades instead of raising
- [x] `compare_metrics` wired into the CLI as `--baseline PATH` rather than deleted — it is the
      Decision-4 regression guard, and being callable only from a scratchpad is what made it look dead
- [x] Rejected: deleting the `temperature`/`seed`/`num_ctx` constructor params (flagged YAGNI).
      They are the knobs the entire B2.0 reproducibility gate rests on.
- [x] New tests: idf-over-pool (verified RED against the old `idf(store)`), the two `--save-memory`
      guards, `n_examples`. 235 passed, ruff clean.
- [x] Re-sweep all 6 arms + a fresh k=0 gate; superseded the k-curve in README and plan §B2 RESULTS.
      **Every headline rate reproduced exactly** — but the proposals under them did not: LOBO
      arms kept only 42/48, 42/48 and 38/48 of their pre-fix selectors, tracking the 5/21, 6/21
      and 10/21 ranking changes the idf fix caused. The re-seeded store was byte-identical, which
      is what proves k=0 was untouched. So the first numbers were right for a partly-invalid
      reason and are now right for a valid one.


### C — UI visual design (deferred, raised 2026-09-05)
The frontend works but looks bad. Functionality is not in question — this is purely visual.
Deferred deliberately: B2 is the differentiating work, and restyling now would churn the same
components again afterwards. Do it after B2, before showing the repo to anyone.

**Decided 2026-09-05** (options presented with tradeoffs, user chose all three) — full plan in
[`.claude/plans/ui-visual-design.md`](../plans/ui-visual-design.md):
Tailwind v4 + shadcn/ui · "quiet developer tool" direction · anchor the popover properly.

- [x] Decide the approach — mechanism, visual direction, and depth all locked
- [x] C0 setup: Tailwind v4 + the Radix primitives shadcn wraps. Written by hand into
      `components/ui/` rather than run through the CLI — same copied-in code, no config rewrite
- [x] C2 tokens in `app/globals.css` `@theme`: warm canvas `#fbfaf9`, deep-green accent `#2f5d50`,
      mono for selectors/values. Explicitly *not* zinc/0.5rem
- [x] C3 shell + layout — `AppShell` (header + centred 1400px column), two-column picker with a
      sticky fields rail, cards instead of `<hr>`s. Confirmed as the biggest single win
- [x] C4 all nine components converted. **70 inline `style={{}}` objects → 2**, and both survivors
      are runtime values that cannot be classes (progress-bar width, popover coordinates)
- [x] C5 popover anchored. `render.py` now posts `getBoundingClientRect()`; `RenderFrame` adds the
      iframe offset and pins a Radix `Popover.Anchor` there. Both render tests still pass
- [x] C6 `HealReview` shows confirmed value → proposed value, with the anchor verdict as its own
      column (`anchor match` / `anchor diverged` / `not in this cluster`)
- [x] C7 four screenshots re-shot through the real stack — upload, pick, batch, heal — driven by
      Playwright against a live backend + arq worker + Ollama. Not mocked screens

**Fixed while shooting:**
- Next's floating dev badge was in the corner of every shot → `devIndicators` off in `next.config.ts`
- README captions were stale against the new shots: they claimed *both* fields failed at 40% and
  that the heal was accepted on a `✓` anchor match. The real run has `title` surviving (0%) and
  the anchor reading *not in this cluster*. Captions rewritten to what the images actually show.

---

## Review

**Phase 8 — Advanced mode COMPLETE (2026-06-18)** — ALL PHASES DONE
- Backend: 143 tests pass, ruff clean. `POST /selector/check` (raw selector → count+values).
- Frontend: AdvancedPanel (custom selector checker + raw JSON config editor w/ validation); build + tsc green.
- MVP (Phases 0.5–5) + headline heal (6) + versioning (7) + advanced (8) all shipped on `dev`.
- Remaining deferred: live heal/bench GATE (needs ANTHROPIC_API_KEY + Ollama) — run at end-of-MVP E2E.

**Phase 7 — Versioning COMPLETE (2026-06-18)**
- Backend: 142 tests pass, ruff clean. `create_config_version` now takes `pg_advisory_xact_lock(hashtext(domain_id))` (§11); `app/versioning.py` diff; `routes/versions.py` (list/diff/pin); `effective_config_version` makes pin actually drive parse/canary/results/heal.
- Advisory lock proven by a concurrency test: two `asyncio.gather`'d creates → versions [1,2], no unique-constraint collision.
- Frontend: VersionPanel (list, diff last two, pin).

**Phase 6 — Heal COMPLETE (2026-06-18)** — the headline feature
- Backend: 139 tests pass, ruff clean. New: `app/heal.py` (trigger/cluster/post-check/provider select), `routes/heal.py` (propose/accept). Reuses spike heal providers + cleaner.
- Anchor-correctness enforced by post-check (§10 step 5), independent of the prompt → robust even with the pre-anchor spike prompt. Statuses healed/suspect/still_broken tested with a FakeProvider.
- `/heal/accept` creates a new config_version (created_by=llm-heal); naive version bump (advisory-lock is Phase 7).
- Frontend: HealReview (value-first §5.7, suspect flagging, per-field accept); build + tsc green.
- Live model = same deferred dependency as the GATE (no ANTHROPIC_API_KEY/Ollama); propose returns model:"unavailable" + the drift, honestly.

**Phase 5 — Async batch + export COMPLETE (2026-06-18)**
- Backend: 134 tests pass, ruff clean. New: `app/batch_parse.py` (run_batch + gather_results), `app/aggregate.py` (rates), `app/export.py` (CSV/JSON), `routes/jobs.py`, `worker.py::batch_parse` arq task.
- Full async E2E through Redis + real arq worker: 2-file zip → job queued→running→done (progress 0→1→2) → price failure_rate 0.5 (abc fails number DQ) → CSV with __file/__item_index.
- CSV bug fixed: empty list gave 0 rows (`max([0])`); floored to 1 row/file.
- Frontend: BatchResults (progress bar, rate table, export links); build + tsc green.

**Phase 4 — Parser + DQ + Anchors COMPLETE (2026-06-18)**
- Backend: 129 tests pass, ruff clean. New: `app/dq.py` (6-status engine), `app/parser.py` (locator-based, single+list), `routes/parse.py` (canary + anchor check).
- Anchor (§10) captured at Confirm (resolved value + descriptor fingerprint); canary compares parsed vs anchor (normalized) → anchor_ok.
- E2E on amazon before.html: price ok + anchor ✓; title ok + anchor correctly flagged divergence vs a wrong hand-anchor (proves the check).
- Frontend: CanaryPanel table (field/value/DQ/anchor), "Test on this file" in FieldPanel; build + tsc green.

**Phase 3 — Inference COMPLETE (2026-06-18)**
- Backend: 118 tests pass, ruff clean. New: `app/presets.py` (12 types + custom), `app/infer.py` (cascade + gated LLM), `routes/infer.py` (POST /infer, GET /presets).
- Cascade tiers: structured 0.95 → regex 0.85 → label 0.70 → LLM 0.60 (opt-in). ✨ returns `llm_unavailable` without a key (honest, unblocked).
- Field config now carries `type` + preset `dq` (DQ *engine* is Phase 4).
- Frontend: PickPopover infers on open, shows type+confidence, Change dropdown, ✨ button; build + tsc green.
- E2E: /infer price(itemprop)=0.95, 6%off=discount_pct 0.85, ✨ no-key=llm_unavailable.

**Phase 2 — Click-to-select COMPLETE (2026-06-18)**
- Backend: 112 tests pass, ruff clean. New: `selector.py` (ladder), `pick.py` (Playwright resolve), `routes/{pick,config}.py`, storage config helpers, overlay click/list-detect JS.
- Architecture: descriptor-based, server-validated — overlay posts element descriptor (script-independent attrs); `/pick/validate` renders raw file and tests candidates via `locator()`. Structural fallback uses `:nth-of-type` (script-robust).
- E2E proof: click price on amazon `before.html` → `css=[data-price-amount='149900']` resolves to 1 = "₹1,49,900"; config saved v1, read back.
- Frontend: `PickPopover` (value + scope + name + Check/Confirm), `FieldPanel` (fields + Save), `RenderFrame` postMessage wiring. build + tsc green.
- Test isolation lesson: unique domain host per test (persistent DB accumulates config versions).

**Phase 1 — Upload + Render COMPLETE (2026-06-18)**
- Backend: 101 tests pass, ruff clean. New modules: `skeleton.py`, `upload.py`, `storage.py`, `routes/{upload,batch}.py`, `render.py::render_snapshot`.
- Security (§14): caps enforced pre-extraction (zip-bomb), filenames sanitized (no traversal), render context aborts all non-file:// requests (no SSRF), snapshot strips scripts + strict CSP, iframe `sandbox="allow-scripts"` (no same-origin).
- Async fix: `NullPool` on the engine — module-global engine + per-test event loops caused "another operation in progress"; NullPool gives a fresh connection per checkout (DB isn't the bottleneck).
- Added dep `python-multipart` (FastAPI form/file parsing).
- Real E2E proof: `curl -F` upload of amazon `before.html` → batch + `dom_skeleton_hash=f07cdd35...` → `/render` returns CSP-locked, overlay-injected snapshot.
- Frontend: upload screen (5.1) + picker shell (iframe + Prev/Next); `build` + `tsc` green. `/pick/[batchId]` dynamic.

**Phase 0.5 — Skeleton COMPLETE (2026-06-18)**
- Backend: 84 tests pass (80 spike + 4 new smoke: health/worker/render/migration), ruff clean.
- DB: Alembic `41f63c59da2d` creates all 6 tables; circular FK (config_version↔upload_batch↔upload_file) broken with `use_alter=True` on the two nullable back-refs.
- Services: Postgres 16 + Redis 7 via `brew services` locally (Docker unavailable); `docker-compose.yml` + CI service containers are the canonical path.
- Frontend: Next.js 15 App Router + TS; `npm run build` + `tsc --noEmit` green; `/` is dynamic (no-store health fetch).
- Real boot proof: `uvicorn app.main:app` → `curl /health` = `{"status":"ok"}`.
- Fixes along the way: bad `build-backend` (`legacy:build`→`build_meta`), venv pip 21→26 for PEP 660 editable, `requires-python` 3.11→3.9 drift.
- Known follow-ups: `npm audit` flags 2 vulns in next 15.1.0 deps (revisit when we add real UI); Playwright smoke is local-only (CI runs `SKIP_PLAYWRIGHT=1`).

**Phase 0 — Heal Spike CODE COMPLETION (2026-06-16)**
- Tests: 74 passed, 6 skipped (Playwright gated), 0 failed
- Coverage: 64% (live-model paths excluded by design)
- Code review fixes applied (5 items): H1 (resolve_but_wrong metric widened), H2 (parse_fail_rate renamed to no_proposal_rate), M1 (number normalization now collapses internal whitespace), L1 (report.py smoke test added), L5 (style nits fixed)
- All spike modules complete: cleaner.py, resolve.py, dq.py, heal/provider.py, heal/{ollama,cloud}_provider.py, bench.py, report.py
- Fixture: 1 real-style synthetic drift case (amazon_product) with before/after HTML + metadata
- Pending: live bench run (Ollama + CloudProvider integration test), GATE decision, real drift pairs
