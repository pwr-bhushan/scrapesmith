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

## Phase 4 — Parser + DQ + anchors

- [ ] Generic parser runs a config in the browser context → `parse_result`
- [ ] DQ engine: `ok | empty | regex_fail | type_fail | range_fail | out_of_scope`
- [ ] Capture field **anchor** (value + fingerprint) on user confirm
- [ ] Canary result panel (5.5); "Re-pick" round-trip back to picker

## Phase 5 — Async batch + per-field rates + export

- [ ] `POST /parse/batch` enqueues arq job over the Playwright pool
- [ ] `GET /jobs/{id}/stream` SSE progress
- [ ] Per-field failure rate + item-level flagged_ratio
- [ ] Batch results screen (5.8)
- [ ] CSV (one row per list item, `__file`/`__item_index` keys) + nested JSON export

## Phase 6 — Heal (cluster → propose → value-first review)

- [ ] Per-field drift trigger (§9): any field failing on ≥30% of items
- [ ] Cluster failing files by `dom_skeleton_hash`; representative = centroid
- [ ] Heal each cluster via provider; anchor values passed in prompt
- [ ] Post-check: valid selector → resolves → DQ → not-too-positional → **anchor match** → 2 more in cluster
- [ ] Drift UI (5.6) + value-first review UI (5.7) with suspect flagging
- [ ] Anti-loop guards (don't re-heal a healed-and-failed skeleton)

## Phase 7 — Versioning

- [ ] Version assignment under `pg_advisory_xact_lock(domain_id)`
- [ ] Version list per domain + diff view
- [ ] Pin batch to specific version (URL param + advanced UI)

## Phase 8 — Advanced mode polish

- [ ] Toggle in header
- [ ] Editable selectors, types, DQ rules
- [ ] Raw JSON config editor with validation
- [ ] Custom selector / custom regex flows

---

## Review

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
