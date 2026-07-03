# Phase 5 — Async Batch Parse + Rates + Progress + Export

> Upload N files, watch live progress, see batch results (5.8), export CSV (one row per list item) +
> nested JSON. Grounds: §7 arq/SSE, §9 per-field rates, §12/§579 output schema.

## Pieces
- `app/batch_parse.py` — `run_batch(session, job_id, batch_id, cv)`: parse every file, store
  `parse_result` rows, update `job.progress={done,total,phase}` after each. Pure-ish, callable
  directly (test) and from the arq task.
- `app/aggregate.py` — `field_rates(results, fields)`: per-field failure_rate = (# items where field
  ∉ ok)/(# in scope); item `flagged_ratio`. Pure, tested.
- `app/export.py` — `csv_rows(results, fields)`: one row per list item, keys `__file`,`__item_index`
  prepended, single-scope fields repeat across an item's rows (§579). `json_tree(results)`:
  `{file: {field: value|[values]}}`. Pure, tested.
- `app/worker.py` — add `batch_parse` arq task wrapping `run_batch` (own DB session).
- `routes/jobs.py` — `POST /parse/batch` (create Job + enqueue arq), `GET /jobs/{id}` (state+progress),
  `GET /jobs/{id}/stream` (SSE poll of job row), `GET /batch/{id}/results` (aggregate),
  `GET /batch/{id}/export.csv|.json`.
- Frontend: `BatchResults` (5.8) — progress bar via SSE, per-field rate table, export links.

## Scope
- **In:** async batch over arq, progress SSE, per-field rates + flagged_ratio, CSV/JSON export.
- **Out:** heal trigger/loop (Phase 6) — rates are computed and shown, but healing is Phase 6.
- Playwright pool sizing stays naive (one context per file, sequential in the worker); §7 bounded pool
  is a later optimization.

## Test strategy
- `run_batch`, `field_rates`, `csv_rows`, `json_tree` tested directly (pg/playwright gated where needed).
- Full arq path verified in E2E: start `arq app.worker.WorkerSettings`, enqueue, poll /jobs/{id}, export.

## Steps: aggregate+export (pure, tests) → batch_parse (test) → worker task → routes → frontend → E2E+commit.
