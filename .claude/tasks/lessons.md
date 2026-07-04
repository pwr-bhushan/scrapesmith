# Scrapesmith — Lessons

Pinned defaults from cross-project experience, plus project-specific learnings as they accrue.

## Cross-Project (pinned day one)

**Environment**
- Use the project toolchain path explicitly (e.g. `.venv/bin/pytest`, `./node_modules/.bin/...`). Bare commands resolve via system PATH and silently use the wrong site-packages.
- Paste the full toolchain path into every subagent prompt. Spawns cold-start and do not inherit shell context.

**Workflow**
- Work on a feature/dev branch, never `main`.
- Implementation wins as ground truth on doc/code drift — update the plan to match the code, unless the code name is genuinely misleading.
- Treat existing tests as locked public contracts. Extend, do not rewrite.

---

## Domain Knowledge

**Workflow autonomy (2026-06-18):** User wants steps driven to completion without pausing for
per-step approval. Do NOT stop and ask "ready to proceed?" between workflow steps — run PLAN →
TESTS → IMPLEMENT → VERIFY → REVIEW → FIX → docs → save straight through. Present the plan once,
then execute. Still pause only for genuine irreversible/destructive decisions or a real blocker.

**Full-build autonomy (2026-06-18):** User authorized proceeding through ALL remaining phases (2→8)
without approval between phases. Commit each phase on `dev` as it completes (durable progress across
context resets). Make reasonable scope decisions up front and record them in the phase plan file
rather than stopping to ask. Keep going until all phases in todo.md are done.

**GATE deferral (2026-06-18):** Phase 0 live bench + GATE deferred to end-of-MVP (run during
whole-app E2E testing). `bench.py` is self-contained; nothing downstream depends on running it.
Build Phases 0.5→5 first, plug in `ANTHROPIC_API_KEY` + Ollama at the end. See phase-0 plan
§"GATE Execution — Deferred".

---

## Coding Lessons

**Python 3.9 compatibility** — `backend/.venv` is pinned to Python 3.9. Avoid 3.10+ only syntax (`|` union types, match statements) unless `from __future__ import annotations` is present at module top. See `heal/provider.py` for correct pattern (type hints as strings or via future import).

**Unit tests must not call live models/Playwright** — gate live dependencies (OllamaProvider calls, CloudProvider API, Playwright browser automation) behind environment checks: `SKIP_PLAYWRIGHT`, `ANTHROPIC_API_KEY` presence, `OLLAMA_HOST`. Tests that bypass gates will silently flatter metrics and fail in CI. Always write a `FakeProvider` to test metric math in isolation.

**Metric classification bugs can silently flatter a GATE** — in the spike, "resolve_but_wrong" was initially counted only on DQ-passing cases. This hid resolving selectors that extracted wrong values but didn't fail DQ. Define metrics to match the plan's stated intent (e.g., "resolve_but_wrong = resolved AND not anchor_correct", period), and explicitly test the boundary cases (DQ-pass-but-wrong, DQ-fail-but-resolved) to avoid gaming the gate.

**HTML cleaner must preserve semantic content** — script/style/comment stripping is safe; stripping data attributes or microdata tags will break `resolve.py` and heal proposals. Test that actual anchor values and search targets survive cleaning.

**SQLAlchemy `Mapped[]` on Python 3.9 needs `typing.Optional`, not `X | None`** — SQLAlchemy resolves Mapped annotations at mapping time, and `str | None` raises on 3.9 even with `from __future__ import annotations`. Use `Optional[str]`. Consequently ruff's `UP007`/`UP045` (which rewrite to `X | None`) are wrong for this codebase — they're in `ignore`. (`backend/app/models.py`.)

**Circular FKs need `use_alter=True`** — the §6 data model has a cycle: `config_version.source_file_id → upload_file → upload_batch → config_version`. Plain `create_table` ordering can't resolve it (alembic warns "unresolvable cycles"; `upgrade head` fails "table does not exist"). Fix: `ForeignKey(..., use_alter=True, name="...")` on the two *nullable* back-refs so those constraints are added via post-create ALTER.

**Editable install needs a valid build backend + modern pip** — `backend/pyproject.toml` had `build-backend = "setuptools.backends.legacy:build"` (invalid) → use `setuptools.build_meta`. Also the venv's pip was 21.2.4; PEP 660 editable installs of pyproject-only projects need pip ≥ 21.3 (`python -m pip install --upgrade pip`).

**Alembic async env + async pytest don't nest** — our `alembic/env.py` online path calls `asyncio.run()`. A test that calls `command.upgrade()` must be a plain `def` (sync), not `async def`, or it fails "asyncio.run() cannot be called from a running event loop". Verify tables afterward via a separate `asyncio.run(...)` with a fresh engine.

**Local infra without Docker** — Docker Desktop isn't installed on this machine; `brew install postgresql@16 redis` + `brew services start` provides pg on 5432 / redis on 6379. `psql` lives at `/opt/homebrew/opt/postgresql@16/bin` (keg-only — add to PATH). Create role+db to match the URL: `CREATE ROLE scrapesmith LOGIN PASSWORD 'scrapesmith' CREATEDB;` + `CREATE DATABASE scrapesmith OWNER scrapesmith;`. `docker-compose.yml` stays the canonical/CI path.

**Integration smoke tests gate on service reachability** — `tests/_svc.py::url_reachable` skips DB/redis tests when the port is closed; Playwright gates on `SKIP_PLAYWRIGHT=1`. Keeps the suite green on a bare machine and lets CI opt in/out per service.

**Async engine + pytest-asyncio needs NullPool** — a module-global `create_async_engine` pools asyncpg connections; pytest-asyncio (auto mode) makes a new event loop per test, so a pooled connection from a prior loop gets reused → `InterfaceError: another operation is in progress` / `Task attached to a different loop`. Fix: `poolclass=NullPool` (fresh connection per checkout). Fine here — render is the bottleneck, not DB. (`backend/app/db.py`.)

**FastAPI form/file uploads need `python-multipart`** — `File(...)`/`Form(...)` params raise at request time without it. It's a runtime dep, add to pyproject.

**Untrusted-HTML render safety (§14)** — three layers: (1) Playwright context `page.route("**/*")` aborts every non-`file://`/`data:` request (no SSRF/egress); (2) snapshot sanitized — strip `<script>`/`<noscript>`, inject strict CSP meta, our overlay is the only inline script; (3) frontend iframe `sandbox="allow-scripts"` WITHOUT `allow-same-origin` (overlay runs, can't touch parent). Never serve raw uploaded HTML to the browser.

**`dom_skeleton_hash` is lossy by design** — drives clustering/dedup only (§10), NOT extraction correctness. Keep tag tree + `role`/`itemprop` + alpha-only class tokens; drop id/data-*/digit-bearing classes so structurally-identical pages collide. Test BOTH directions (same-structure→equal, different-structure→differ). (`backend/app/skeleton.py`.)

**Sandboxed iframe ⇒ descriptor-based picking** — the render iframe is `sandbox="allow-scripts"` (no same-origin), so the parent can't read its DOM. Click-to-select works by the overlay computing an element *descriptor* (attrs are script-independent) and `postMessage`-ing to the parent; the backend regenerates + validates selectors against the RAW render. Don't try to transfer absolute DOM paths between the sanitized snapshot and the raw page — script removal shifts indices. Structural fallback uses `:nth-of-type` (same-tag count, script-robust), never `nth-child`. (`app/render.py` overlay, `app/selector.py`, `app/pick.py`.)

**Persistent DB ⇒ tests must self-isolate** — the local Postgres isn't reset between runs, so tests that assert absolute state (e.g. `config version == 1`) break on re-run when a get-or-create domain accumulates rows. Use a unique key per test (e.g. `host=f"{uuid4().hex}.com"`). Gate on `url_reachable` as usual. (`tests/test_config_routes.py`.)

**Playwright `locator()` accepts prefixed & plain CSS** — `page.locator("main .price")` and `page.locator("css=main .price")` both work; store selectors engine-prefixed (`css=`/`xpath=`) per §6 and pass straight to locator. `.count()` gives resolve cardinality (1 = unique single, N = list). (`app/pick.py`.)

**arq background task pattern** — the arq worker is a separate process (`.venv/bin/arq app.worker.WorkerSettings`). Factor real work into a plain async fn (`run_batch`) callable directly in tests; the arq task is a thin wrapper that opens its OWN `SessionLocal` and marks the Job `failed` on exception (else it dies silently). Enqueue from the API via `create_pool` + `enqueue_job(name, *args)`; args must be JSON-serializable (pass uuids as str). (`app/worker.py`, `app/batch_parse.py`, `routes/jobs.py`.)

**Per-domain advisory lock for versioning (§11)** — `create_config_version` runs `SELECT pg_advisory_xact_lock(hashtext(:domain_id_text))` before computing `max(version)+1`, so concurrent saves/heals serialize instead of colliding on `unique(domain_id, version)`. Proven by a test that `asyncio.gather`s two creates for the same domain and asserts versions `[1,2]`. (`app/storage.py`.)

**Anchor-correctness belongs in the post-check, not the prompt** — heal validates a proposed selector in code (§10 steps 1–6): valid prefix → resolves → DQ → not-too-positional (`:nth-child`/>1 index) → **anchor match (normalized)** → 2 more cluster files. A proposal that passes DQ but diverges from the anchor is `suspect`, never auto-applied. This makes heal robust even though the reused spike prompt predates anchors. (`app/heal.py`.)

**`effective_config_version` = pinned else latest** — a batch runs against `batch.config_version_id` when set (pin, §11), else the domain's latest. Route parse/canary/results/heal through it so pinning actually takes effect. `save_config`/`heal_accept` set it to the new version (== latest at that moment). (`app/storage.py`.)

**Full-build status (2026-06-18):** Phases 0.5→8 all shipped on `dev` (commits db06335…960efbc). 143 backend tests, ruff clean, frontend build+tsc green. Only deferred item: the live heal/bench GATE (needs ANTHROPIC_API_KEY + Ollama) — run at end-of-MVP E2E. See [[full-build-autonomy]] note above.
