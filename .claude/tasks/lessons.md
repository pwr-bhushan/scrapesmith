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

(populate as user clarifies domain decisions)

---

## Coding Lessons

**Python 3.9 compatibility** — `backend/.venv` is pinned to Python 3.9. Avoid 3.10+ only syntax (`|` union types, match statements) unless `from __future__ import annotations` is present at module top. See `heal/provider.py` for correct pattern (type hints as strings or via future import).

**Unit tests must not call live models/Playwright** — gate live dependencies (OllamaProvider calls, CloudProvider API, Playwright browser automation) behind environment checks: `SKIP_PLAYWRIGHT`, `ANTHROPIC_API_KEY` presence, `OLLAMA_HOST`. Tests that bypass gates will silently flatter metrics and fail in CI. Always write a `FakeProvider` to test metric math in isolation.

**Metric classification bugs can silently flatter a GATE** — in the spike, "resolve_but_wrong" was initially counted only on DQ-passing cases. This hid resolving selectors that extracted wrong values but didn't fail DQ. Define metrics to match the plan's stated intent (e.g., "resolve_but_wrong = resolved AND not anchor_correct", period), and explicitly test the boundary cases (DQ-pass-but-wrong, DQ-fail-but-resolved) to avoid gaming the gate.

**HTML cleaner must preserve semantic content** — script/style/comment stripping is safe; stripping data attributes or microdata tags will break `resolve.py` and heal proposals. Test that actual anchor values and search targets survive cleaning.
