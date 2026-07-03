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
