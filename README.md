# Scrapesmith

Self-healing HTML parser. Upload raw HTML (single file or gzipped batch), pick the fields you care about by clicking on a rendered preview, and the system extracts them across the whole batch. When a site's markup drifts and parses start failing, a local LLM rebuilds the selector config automatically.

**Status:** planning. See [`.claude/plans/self-healing-parser.md`](.claude/plans/self-healing-parser.md).

## Stack

- **Backend:** Python 3.12, FastAPI (async), SQLAlchemy, Postgres, Redis + arq (jobs)
- **Rendering / extraction:** Playwright (headless Chromium) — the single source of truth for the DOM, so selectors picked in the preview resolve identically at extract time
- **Frontend:** Next.js (React + TypeScript)
- **LLM:** pluggable heal provider — local model via Ollama by default, cloud model (e.g. Claude) configurable

## Layout

```
backend/     FastAPI service: ingest, parse, heal, config CRUD
frontend/    Next.js app: upload + click-to-select UI
docs/        Architecture diagrams, wireframes
.claude/     Plans, tasks, lessons
```
