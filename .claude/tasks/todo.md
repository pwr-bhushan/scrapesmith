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

⚠️ Headroom is still only 8.33% (4/48). B2 must show a trend across the k-sweep, not a 1-field delta.

### B2 — Heal memory (not started)
- [ ] `paths()` signature + TF-IDF cosine retriever over `artifacts/heal_memory.jsonl`
- [ ] Inject top-k into `build_prompt`; `--k` on the CLI
- [ ] Sweep k ∈ {0,1,3,5}; `compare_metrics` regression guard; before/after table in the README

### C — UI visual design (deferred, raised 2026-09-05)
The frontend works but looks bad. Functionality is not in question — this is purely visual.
Deferred deliberately: B2 is the differentiating work, and restyling now would churn the same
components again afterwards. Do it after B2, before showing the repo to anyone.

- [ ] Decide the approach first (design system vs. hand-rolled Tailwind pass) — the screenshots in
      `docs/img/` are in the README, so whatever lands here has to be re-shot
- [ ] Components in scope: upload, picker + `PickPopover`, canary, batch results, `HealReview`,
      `VersionPanel`, advanced mode
- [ ] Re-shoot the four README screenshots afterwards

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
