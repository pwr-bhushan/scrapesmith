# Scrapesmith — Todo

Tracks active phases from [`.claude/plans/self-healing-parser.md`](../plans/self-healing-parser.md).

## Phase 0 — Skeleton

- [ ] FastAPI app boots with `/health`
- [ ] Postgres connection + first migration (`domain`, `config_version`, `upload_batch`, `upload_file`, `parse_result`)
- [ ] Next.js app boots with shared API client
- [ ] Ollama smoke test from backend
- [ ] CI: lint + pytest + frontend type-check

## Phase 1 — Upload + render

- [ ] `POST /upload` accepts single `.html` or `.gz` archive
- [ ] Files persisted to `./uploads/{batch_id}/`
- [ ] `dom_skeleton_hash` computed per file
- [ ] Frontend upload screen (wireframe 5.1)
- [ ] Iframe sandbox render of file N with Prev/Next

## Phase 2 — Click-to-select

- [ ] Inject click listener into sandboxed iframe (srcdoc same-origin)
- [ ] Strip `<script>` + inline handlers before render
- [ ] Selector generator (`@medv/finder` or port) — prefer id/data-*/itemprop
- [ ] Side panel adds field on click (manual name in this phase)
- [ ] Save config v1 to DB

## Phase 3 — Inference + presets

- [ ] Backend `/infer` endpoint with microdata → regex → label-proximity → LLM cascade
- [ ] Field type presets library shipped (`title`, `price`, `discount_pct`, ...)
- [ ] Popover UI (wireframe 5.3) with confidence and Change dropdown
- [ ] List-vs-single detection (common-ancestor walk)

## Phase 4 — Parser + DQ

- [ ] Generic parser executes a config against one file → `parse_result`
- [ ] DQ engine: `ok | empty | regex_fail | type_fail | range_fail`
- [ ] Canary result panel (wireframe 5.5)
- [ ] "Re-pick" round-trip back to picker

## Phase 5 — Batch + flagged ratio

- [ ] Parallel parse across all files in a batch
- [ ] Compute `flagged_ratio` per item and per batch
- [ ] Batch results screen (wireframe 5.8)
- [ ] CSV + JSON export endpoints

## Phase 6 — LLM heal

- [ ] HTML cleaner (strip scripts/styles/comments/whitespace)
- [ ] Heal prompt + JSON-mode call to Ollama
- [ ] Post-check (XPath validity, resolves, DQ pass, not-too-positional, 2-file confirm)
- [ ] Drift trigger UI (5.6) + heal review UI (5.7)
- [ ] Anti-loop guard via `dom_skeleton_hash`

## Phase 7 — Versioning

- [ ] Version list per domain
- [ ] Diff view between two versions
- [ ] Pin batch to specific version (URL param + advanced UI)

## Phase 8 — Advanced mode polish

- [ ] Toggle in header
- [ ] Editable selectors, types, DQ rules
- [ ] Raw JSON config editor with validation
- [ ] Custom XPath / custom regex flows

---

## Review

(populate when phases complete)
