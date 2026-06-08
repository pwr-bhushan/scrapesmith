# Scrapesmith

Self-healing HTML parser. Upload raw HTML (single file or gzipped batch), pick the fields you care about by clicking on a rendered preview, and the system extracts them across the whole batch. When a site's markup drifts and parses start failing, a local LLM rebuilds the selector config automatically.

**Status:** planning. See [`.claude/plans/self-healing-parser.md`](.claude/plans/self-healing-parser.md).

## Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy, Postgres, lxml/BeautifulSoup
- **Frontend:** Next.js (React + TypeScript)
- **LLM:** local model via Ollama (configurable)

## Layout

```
backend/     FastAPI service: ingest, parse, heal, config CRUD
frontend/    Next.js app: upload + click-to-select UI
docs/        Architecture diagrams, wireframes
.claude/     Plans, tasks, lessons
```
