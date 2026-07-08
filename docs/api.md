# API Reference

Base URL: `http://localhost:8000`. All bodies are JSON unless noted. Interactive docs are auto-generated at **`/docs`** (Swagger) and **`/redoc`**; the schema is at `/openapi.json`.

Selectors are engine-prefixed (`css=…` / `xpath=…`) and passed straight to Playwright `locator()`.

---

## Health

### `GET /health`
→ `200 {"status": "ok"}`

---

## Upload & batch

### `POST /upload` — ingest HTML
`multipart/form-data`:

| field | type | notes |
|-------|------|-------|
| `file` | file | `.html`, `.gz`, or `.zip` (archive of HTML) |
| `host` | str | e.g. `amazon.in` |
| `page_type` | str | e.g. `product_listing` |
| `render_js` | bool | run page scripts on render (default `true`) |
| `notes` | str | optional |

→ `{ "batch_id", "domain_id", "file_count", "files": [{ "index", "filename" }] }`
`400` on cap breach (size / file-count / uncompressed total — zip-bomb guard) or invalid gzip.

### `GET /batch/{batch_id}`
→ `{ "batch_id", "domain_id", "status", "file_count", "files": [{ "index", "filename", "dom_skeleton_hash" }] }`

### `GET /batch/{batch_id}/file/{index}/render`
→ `text/html` — a sanitized, CSP-locked, overlay-injected snapshot of the file rendered headless. Serve inside a sandboxed iframe. `404` if the file index doesn't exist.

---

## Pick & selectors

### `POST /pick/validate` — descriptor → validated selector
```json
{ "batch_id": "…", "index": 0, "scope": "single",
  "descriptor": { "tag": "span", "id": "", "classes": ["price"],
                  "data": {"data-price-amount": "149900"},
                  "itemprop": "price", "role": "", "landmark": "main", "nth_of_type": 1 },
  "list_parent_selector": null }
```
Generates candidate selectors via the stability ladder and returns the first that resolves uniquely (`scope: "single"` → count 1) or as a list (`scope: "list"` → count ≥ 2, requires `list_parent_selector`).
→ `{ "resolves": true, "selector": "css=[itemprop='price']", "count": 1, "values": ["₹1,49,900"], "scope": "single", "list_parent_selector": null }`
If nothing resolves uniquely, `resolves: false` with the best attempt.

### `POST /selector/check` — resolve a hand-written selector (advanced mode)
```json
{ "batch_id": "…", "index": 0, "selector": "css=[data-price-amount]" }
```
→ `{ "count": 1, "values": ["₹1,49,900"], "resolves": true }`

---

## Inference

### `POST /infer` — classify a clicked element
```json
{ "text": "₹1,49,900", "itemprop": "price", "data": {}, "label": "", "use_llm": false }
```
Cascade: structured (0.95) → text regex (0.85) → label proximity (0.70) → LLM (0.60, only if `use_llm` and no deterministic hit).
→ `{ "type": "price", "confidence": 0.95, "source": "structured", "dq": { "required": true, "parses_as": "number", "range": [0, null] } }`
No hit → `type: null, source: "none"`. `✨` with no model configured → `source: "llm_unavailable"`.

### `GET /presets`
→ `{ "types": ["title", "price", "discount_pct", …, "custom"] }`

---

## Config

A **ConfigField**:
```json
{ "name": "price", "selector": "css=[data-price-amount]", "scope": "single",
  "list_parent_selector": null, "type": "price",
  "dq": { "required": true, "parses_as": "number", "range": [0, null] },
  "anchor": { "value": "₹1,49,900", "fingerprint": { … } } }
```

### `POST /batch/{batch_id}/config` — save a new config version
`{ "fields": [ ConfigField, … ] }` → `{ "config_version_id", "version", "field_count" }`. `400` if empty.

### `GET /batch/{batch_id}/config`
→ `{ "config_version_id", "version", "fields": [ … ] }` (latest for the batch's domain; `version: null` if none).

---

## Parse

### `POST /parse/canary` — run the config on one file
`{ "batch_id": "…", "index": 0 }`
→ `{ "file_index", "filename", "config_version", "data": {field: value|[values]},
     "field_status": {field: status}, "flags": {field: [reason]}, "anchor_ok": {field: true|false|null} }`
`anchor_ok` is `null` when the field has no anchor. Stores a `parse_result` row.

### `POST /parse/batch` — async batch over all files
`{ "batch_id": "…" }` → `{ "job_id", "config_version" }`. Enqueues an arq job; requires a running worker.

---

## Jobs, results, export

### `GET /jobs/{job_id}`
→ `{ "job_id", "state": "queued|running|done|failed", "progress": {"done", "total", "phase"}, "error": null }`

### `GET /jobs/{job_id}/stream`
→ `text/event-stream` — SSE, one `data: {"state", "progress"}` event ~every 0.5 s until `done`/`failed`.

### `GET /batch/{batch_id}/results`
→ `{ "config_version", "file_count",
     "field_rates": {field: {"failures", "in_scope", "failure_rate"}},
     "flagged": [{"file", "flagged_ratio"}],
     "rows": [{"file", "path", "dom_skeleton_hash", "data", "field_status", "flags"}] }`

### `GET /batch/{batch_id}/export.csv`
→ `text/csv` — one row per list item; columns `__file, __item_index, <fields…>`. Single-scope fields repeat across an item's rows.

### `GET /batch/{batch_id}/export.json`
→ `{ "<filename>": { "<field>": value | [values] }, … }`

---

## Heal

### `POST /heal/propose` — detect drift, cluster, propose, post-check
`{ "batch_id": "…" }`
→ if no field is over threshold: `{ "triggered": false, "field_rates": {…} }`
→ otherwise:
```json
{ "triggered": true, "failing": ["price"], "field_rates": {…},
  "clusters": [ { "hash": "…", "size": 3, "representative": "f12.html", "model": "cloud/claude-haiku-4-5",
    "proposals": { "price": { "selector": "css=[data-price]", "status": "healed",
                              "value": "₹1,49,900", "anchor_ok": true, "anchor": "₹1,49,900" } } } ] }
```
`status ∈ {healed, suspect, still_broken}`. With no model configured, `model: "unavailable"` and empty `proposals` (the drift is still reported). Never auto-applies.

### `POST /heal/accept` — write accepted selectors as a new version
`{ "batch_id": "…", "accepted": { "price": "css=[data-price]" } }`
→ `{ "config_version_id", "version", "healed": ["price"] }` (`created_by = llm-heal`).

---

## Versions

### `GET /domains/{domain_id}/versions`
→ `{ "versions": [{ "id", "version", "created_by", "parent_version", "field_count" }] }`

### `GET /domains/{domain_id}/diff?a=1&b=2`
→ `{ "a", "b", "diff": { "added": [names], "removed": [names],
     "changed": { field: { key: [old, new] } } } }` — `404` if a version is missing.

### `POST /batch/{batch_id}/pin`
`{ "version": 1 }` → `{ "batch_id", "pinned_version" }`. Subsequent parse/canary/results/heal use the pinned version instead of latest.
