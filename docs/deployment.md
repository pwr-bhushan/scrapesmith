# Deployment & Operations

How to run Scrapesmith locally, in CI, and what to harden before production.

## Stack

| Layer | Tech |
|-------|------|
| Backend | Python 3.9, FastAPI (async), SQLAlchemy 2 (async) + asyncpg, Alembic |
| Data / jobs | Postgres 16, Redis 7 + arq |
| Rendering | Playwright (headless Chromium) |
| Frontend | Next.js 15 (App Router, TypeScript) |
| Heal LLM | Ollama (default) / cloud Claude (opt-in) |

## Prerequisites

- Python **3.9** (the venv is pinned to 3.9; avoid 3.10+ syntax)
- Node 18+ (developed on 22/25)
- Postgres 16 and Redis 7 — via Docker **or** local services
- Chromium for Playwright (`playwright install chromium`)

## 1. Infrastructure

**Docker (canonical):**
```bash
docker compose up -d          # postgres:16 on 5432, redis:7 on 6379 (see docker-compose.yml)
```

**Or local services (no Docker):**
```bash
brew install postgresql@16 redis
brew services start postgresql@16 redis
# create the role + db the default URL expects:
psql -d postgres -c "CREATE ROLE scrapesmith LOGIN PASSWORD 'scrapesmith' CREATEDB;"
psql -d postgres -c "CREATE DATABASE scrapesmith OWNER scrapesmith;"
# (psql lives at /opt/homebrew/opt/postgresql@16/bin on Apple Silicon)
```

## 2. Backend

```bash
cd backend
python3.9 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/playwright install chromium
.venv/bin/alembic upgrade head                       # create the 6 tables
```

Run the API and the worker (two processes):
```bash
.venv/bin/uvicorn app.main:app --reload              # http://localhost:8000
.venv/bin/arq app.worker.WorkerSettings              # background batch/heal jobs
```

The arq worker is **required** for `POST /parse/batch` — without it, jobs stay `queued`. Canary parse (`/parse/canary`) runs synchronously and needs no worker.

## 3. Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local     # NEXT_PUBLIC_API_BASE=http://localhost:8000
npm run dev                          # http://localhost:3000
```

## Configuration (environment)

| Variable | Default | Purpose |
|----------|---------|---------|
| `SCRAPESMITH_DATABASE_URL` | `postgresql+asyncpg://scrapesmith:scrapesmith@localhost:5432/scrapesmith` | async Postgres DSN |
| `SCRAPESMITH_REDIS_URL` | `redis://localhost:6379` | arq queue + job state |
| `ANTHROPIC_API_KEY` | — | enables the cloud heal provider (Claude) |
| `SCRAPESMITH_CLOUD_MODEL` | `claude-haiku-4-5` | cloud model id |
| `OLLAMA_HOST` | `http://localhost:11434` | enables the local heal provider |
| `NEXT_PUBLIC_API_BASE` | `http://localhost:8000` | API base for the frontend |
| `SKIP_PLAYWRIGHT` | — | set `1` to skip browser-dependent tests |

Heal provider selection: `ANTHROPIC_API_KEY` → cloud, else `OLLAMA_HOST` → Ollama, else none (heal returns `model: "unavailable"`).

## Database migrations

Alembic env is async and reads the URL/metadata from the app package.
```bash
.venv/bin/alembic upgrade head                       # apply
.venv/bin/alembic revision --autogenerate -m "…"     # new migration from model changes
```
Note: the `config_version ↔ upload_batch ↔ upload_file` circular FK uses `use_alter`, so the initial migration applies without ordering errors.

## Tests

```bash
cd backend && .venv/bin/pytest        # 143 tests
.venv/bin/ruff check .
cd frontend && npm run typecheck && npm run build
```

Integration tests gate on service reachability (`tests/_svc.py`) — DB/Redis tests skip if the port is closed, Playwright tests skip on `SKIP_PLAYWRIGHT=1` — so the suite stays green on a bare machine.

## CI

[`.github/workflows/ci.yml`](../.github/workflows/ci.yml) runs on push/PR to `main`/`dev`:
- **backend** — spins up `postgres:16` + `redis:7` service containers, `pip install -e '.[dev]'`, `ruff check .`, `pytest` (with `SKIP_PLAYWRIGHT=1` — the browser smoke stays local).
- **frontend** — `npm install`, `tsc --noEmit`.

## Storage

Uploaded HTML is written to `backend/uploads/{batch_id}/{index}_{filename}` (gitignored); the DB stores the path, `sha256`, and `dom_skeleton_hash`. For multi-node deployments this needs shared/object storage — see below.

## Before production

Deferred hardening (tracked in the design spec §14/§7 and the phase plans):

- **Heal GATE** — wire a real model (`ANTHROPIC_API_KEY` or Ollama) and validate against real drift pairs before relying on auto-heal. All model-independent code is done; healing degrades honestly to `model: "unavailable"` without a provider.
- **SSRF egress proxy** — the render context blocks all non-`file://` requests today; a production setup that fetches external assets needs the proxy that denies private/loopback/link-local ranges (§14).
- **Playwright pool sizing** — rendering is currently one context per file, sequential in the worker; a bounded persistent pool with backpressure is the §7 scale path.
- **Auth & rate limiting** — there is no authentication or per-endpoint rate limiting yet.
- **Shared upload storage** — move `backend/uploads/` to object storage for multi-worker/multi-node runs.
- **CORS** — the API currently allows all origins for dev; lock this down.
