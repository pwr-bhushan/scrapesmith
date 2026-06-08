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

(populate after corrections / code-review findings)
