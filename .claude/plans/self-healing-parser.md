# Self-Healing Parser — Plan

**Status:** draft v1
**Owner:** Bhushan
**Last updated:** 2026-06-08

---

## 1. Goal

Let a non-technical user upload a batch of HTML files for a given domain, click on the data points they care about in a rendered preview, and get back a structured extraction across the entire batch. When site markup drifts and extractions start failing, the system rebuilds its own selector config with a local LLM — no engineer in the loop.

## 2. Non-goals (v1)

- Live crawling / URL fetching — input is HTML (or a `.gz` archive of HTML files) only.
- JS-rendered SPAs — we parse the HTML as received. If the user supplies a server-rendered snapshot, great; we don't run a headless browser.
- Multi-tenant auth — single-user / local deployment.
- Cross-domain config sharing — configs are scoped to one domain.

## 3. Personas

| Persona | What they do | What they see |
|---|---|---|
| **Operator** (default) | Uploads files, clicks elements, reviews flagged items. Doesn't know XPath. | Simple mode: field list with friendly names + sample values. |
| **Power user** (toggle) | Same as Operator + can edit selectors, regexes, DQ rules, scope, raw config JSON. | Advanced mode: everything Operator sees + selectors, types, DQ rules, version history. |

## 4. End-to-end flow (happy path)

```
┌─────────┐   ┌──────────┐   ┌───────────────┐   ┌──────────┐   ┌─────────┐
│ Upload  │ → │ Pick     │ → │ Canary parse  │ → │ Batch    │ → │ Export  │
│ + domain│   │ fields   │   │ on 1–3 files  │   │ parse    │   │ CSV/JSON│
└─────────┘   └──────────┘   └───────┬───────┘   └────┬─────┘   └─────────┘
                                     │ DQ fails       │ DQ fails on
                                     │ on canary      │ ≥X% of items
                                     ▼                ▼
                              ┌──────────────┐  ┌────────────┐
                              │ Re-pick or   │  │ Auto-heal  │
                              │ adjust       │  │ via LLM    │
                              └──────────────┘  └────────────┘
```

Two healing entry points:
- **Build-time healing** — config doesn't even parse its own canary file. Reopen the UI.
- **Drift healing** — config worked before but a new batch fails. LLM rebuilds, user reviews diff.

If config already exists for the domain, upload skips straight to canary parse. The user only sees the picker UI when there's no config or healing is triggered.

---

## 5. UI Wireframes

### 5.1 Upload screen

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Scrapesmith                                              [⚙ Settings]   │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│                ┌────────────────────────────────────┐                    │
│                │                                    │                    │
│                │    ⬆   Drop HTML or .gz here       │                    │
│                │         or click to browse         │                    │
│                │                                    │                    │
│                └────────────────────────────────────┘                    │
│                                                                          │
│     Domain:    [ amazon.in_________________________ ]                    │
│     Page type: [ product_listing  ⌄ ]   (auto-detected from first file)  │
│     Notes:     [ optional_______________________________ ]               │
│                                                                          │
│     ℹ  Found existing config for amazon.in / product_listing (v3).       │
│        Will use it for canary parse first.                               │
│                                                                          │
│                                                       [ Continue → ]     │
└──────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Field picker — Simple mode (no config exists)

```
┌────────────────────────────────────────────────────────────────────────────────┐
│  amazon.in / product_listing  •  Building config  •  Simple [Advanced ⌄]      │
├──────────────────────────────────────────────────────┬─────────────────────────┤
│                                                      │  Fields                 │
│  ┌────────────────────────────────────────────────┐  │  ──────                 │
│  │ [iframe — sandboxed render of file 1]          │  │  ✓ Title                │
│  │                                                │  │    "iPhone 15 Pro Max"  │
│  │   Apple iPhone 15 Pro Max     ← click          │  │                         │
│  │   ★★★★☆ (12,341 reviews)                       │  │  ✓ Price                │
│  │   ₹1,49,900                                    │  │    "₹1,49,900"          │
│  │   M.R.P.: ₹1,59,900  (6% off)                  │  │                         │
│  │   In stock                                     │  │  ✓ Rating               │
│  │   [Add to Cart]                                │  │    "4.3"                │
│  │                                                │  │                         │
│  │   ╭─ pre-highlight (microdata) ─╮              │  │  + Add another field    │
│  │   │ green outline on itemprop  │              │  │                         │
│  │   ╰────────────────────────────╯              │  │  ─────────────────────  │
│  └────────────────────────────────────────────────┘  │  Done picking?          │
│                                                      │  [ Test on this file ]  │
│  File 1 of 47    ◀ Prev    Next ▶                    │                         │
└──────────────────────────────────────────────────────┴─────────────────────────┘
```

### 5.3 Click popover (appears on any click in iframe)

```
            ┌────────────────────────────────┐
            │ Looks like:  PRICE      (89%)  │
            │                                │
            │ Value: "₹1,49,900"             │
            │                                │
            │ Scope:                         │
            │   ● Just this one              │
            │   ○ All 24 similar items       │
            │                                │
            │ Field name: [ price________ ]  │
            │                                │
            │   [ Confirm ]    [ Change ⌄ ]  │
            └────────────────────────────────┘

  "Change ⌄" expands to: title • price • discount_pct • image
                         • description • rating • availability
                         • brand • date • url • custom...
```

### 5.4 Field picker — Advanced mode (right panel only — left iframe unchanged)

```
│  Fields                                                       │
│  ──────                                                       │
│  ✓ Title                                       [edit] [×]    │
│      Selector: //h1[@id='productTitle']                       │
│      Type:     text                                           │
│      Scope:    single                                         │
│      DQ:       non-empty • min_len=3                          │
│                                                               │
│  ✓ Price                                       [edit] [×]    │
│      Selector: //*[@itemprop='price']                         │
│      Type:     currency                                       │
│      Scope:    list (24 matches)                              │
│      DQ:       non-empty • regex=[₹$€]\s*[\d,]+               │
│                parses-as-number                               │
│                                                               │
│  ✓ Rating                                      [edit] [×]    │
│      Selector: //span[@class='a-icon-alt']                    │
│      Type:     rating                                         │
│      DQ:       between 0 and 5                                │
│                                                               │
│  + Add field   ⌃ Add field with custom XPath                  │
│                                                               │
│  ───────────────────────────────────────────                  │
│  Raw config JSON     [ View ] [ Edit ]                        │
│  Version history     v3 (current) • v2 • v1                   │
```

### 5.5 Canary test result (one file parsed before batch)

```
┌──────────────────────────────────────────────────────────────────────┐
│  Canary test — file 1 of 47                                          │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   3 / 4 fields OK    1 flagged                                       │
│                                                                      │
│   ✓ Title         "Apple iPhone 15 Pro Max"                          │
│   ✓ Price         "₹1,49,900"                                        │
│   ⚠ Discount %    (empty)              [ Show element ] [ Re-pick ] │
│   ✓ Rating        "4.3"                                              │
│                                                                      │
│   ┌─ Why flagged ────────────────────────────────────────────┐      │
│   │ Selector returned no match. Element may have moved or    │      │
│   │ the markup has changed. Try re-picking on this file.     │      │
│   └──────────────────────────────────────────────────────────┘      │
│                                                                      │
│                            [ Edit config ]   [ Run batch → ]         │
└──────────────────────────────────────────────────────────────────────┘
```

### 5.6 Drift detected → healing prompt

```
┌──────────────────────────────────────────────────────────────────────┐
│  ⚠  Drift detected                                                   │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   In 12 / 47 files (25.5%), more than half of the fields failed      │
│   the data-quality check. The site's markup likely changed.          │
│                                                                      │
│   ┌─ Current config v3  (created 2026-05-12) ─────────────┐         │
│   │   4 fields  •  failing: price, discount_pct           │         │
│   └────────────────────────────────────────────────────────┘         │
│                                                                      │
│   What would you like to do?                                         │
│     ● Auto-heal with local LLM, then re-run     (recommended)        │
│     ○ Open the picker and re-do it myself                            │
│     ○ Skip — keep partial results                                    │
│                                                                      │
│                                              [ Start auto-heal → ]   │
└──────────────────────────────────────────────────────────────────────┘
```

### 5.7 Healing review (after LLM returns)

```
┌──────────────────────────────────────────────────────────────────────┐
│  Healed config — review before applying                              │
│  amazon.in / product_listing   v3 → v4 (proposed)                    │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   Field        v3 selector                v4 selector       Status   │
│   ─────        ────────────                ────────────      ──────  │
│   title        //h1[@id='productTitle']    (unchanged)       =       │
│   price        //*[@itemprop='price']      //span[@data-     CHANGE  │
│                                            -price-amount]            │
│   discount_pct //span.savingsPercentage    //*[@data-savings  CHANGE │
│                                            -percent]                 │
│   rating       //span[@class='a-icon-alt'] (unchanged)       =       │
│                                                                      │
│   Sample re-parse on file 7:                                         │
│     ✓ title "Apple iPhone 15 Pro Max"                                │
│     ✓ price "₹1,49,900"                                              │
│     ✓ discount_pct "6%"                                              │
│     ✓ rating "4.3"                                                   │
│                                                                      │
│        [ Reject — keep v3 ]      [ Accept v4 and re-run batch → ]    │
└──────────────────────────────────────────────────────────────────────┘
```

### 5.8 Batch results

```
┌──────────────────────────────────────────────────────────────────────┐
│  Batch complete  •  amazon.in / product_listing  •  config v4       │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   47 files     45 fully OK     2 partial     0 failed                │
│                                                                      │
│   Field coverage:                                                    │
│     title         ████████████████████  100%                         │
│     price         ███████████████████░   95%                         │
│     discount_pct  █████████████████░░░   85%                         │
│     rating        ████████████████████  100%                         │
│                                                                      │
│   [ Download CSV ]  [ Download JSON ]  [ View flagged items (2) ]    │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 6. Data model

```sql
-- a logical site/page-type combo (e.g. amazon.in + product_listing)
domain(
  id              uuid pk,
  host            text not null,           -- "amazon.in"
  page_type       text not null,           -- "product_listing", "search", etc.
  created_at      timestamptz,
  unique(host, page_type)
)

-- one row per saved config version; latest_version_id on domain (denorm) for speed
config_version(
  id              uuid pk,
  domain_id       uuid fk -> domain,
  version         int not null,            -- monotonic per domain
  created_at      timestamptz,
  created_by      text,                    -- 'user' | 'llm-heal' | 'llm-bootstrap'
  source_file_id  uuid fk -> upload_file,  -- which file it was built/healed on
  fields          jsonb not null,          -- see ConfigField schema below
  parent_version  int,                     -- for diffs
  notes           text,
  unique(domain_id, version)
)

-- ConfigField (jsonb element shape)
-- {
--   "name": "price",
--   "type": "currency",                  -- one of FIELD_TYPES
--   "selector": "//*[@itemprop='price']",
--   "selector_kind": "xpath" | "css",
--   "scope": "single" | "list",
--   "list_parent_selector": null | "...", -- for list scope, common ancestor
--   "dq": {
--     "required": true,
--     "regex": "[₹$€]\\s*[\\d,]+",
--     "parses_as": "number",
--     "min_len": 1,
--     "max_len": null,
--     "range": [0, 5]                    -- for numeric types
--   }
-- }

-- an upload batch (zip or single file)
upload_batch(
  id              uuid pk,
  domain_id       uuid fk -> domain,
  config_version_id uuid fk -> config_version null,  -- which config was used
  file_count      int,
  status          text,                    -- pending|canary|healing|running|done|failed
  created_at      timestamptz
)

upload_file(
  id              uuid pk,
  batch_id        uuid fk -> upload_batch,
  filename        text,
  sha256          text,
  dom_skeleton_hash text,                  -- tag-tree-only hash, for drift detection
  raw_html_path   text                     -- on-disk path; we don't bloat the DB
)

parse_result(
  id              uuid pk,
  file_id         uuid fk -> upload_file,
  config_version_id uuid fk -> config_version,
  data            jsonb,                   -- {field_name: extracted_value}
  flags           jsonb,                   -- {field_name: [reason, ...]}
  flagged_ratio   numeric,                 -- 0..1, share of fields that failed DQ
  created_at      timestamptz
)
```

**Why `dom_skeleton_hash`:** we need to detect that "site changed" cheaply, and avoid re-healing on a structure we already failed on. Hash = tag tree only (tags + structural attributes like `id`, `data-*`, semantic class roots), no text. Identical skeletons → identical structure → same heal result, so dedup.

---

## 7. Service architecture

```
┌─────────────────┐    ┌────────────────────────────────────────────┐
│  Next.js (UI)   │◀──▶│  FastAPI                                   │
│                 │    │  ├─ /upload                  ingest         │
│  - iframe srcdoc│    │  ├─ /config/{domain}         CRUD          │
│  - click capture│    │  ├─ /parse/canary            single file   │
│  - field panel  │    │  ├─ /parse/batch             full run      │
│  - popover      │    │  ├─ /heal/propose            LLM call      │
│                 │    │  └─ /export/{batch}.csv|json               │
└─────────────────┘    │                                            │
                       │  modules:                                  │
                       │   parser/        lxml + selectors          │
                       │   inference/     click → field type        │
                       │   dq/            regex + type validators   │
                       │   heal/          LLM prompt + post-check   │
                       │   storage/       sqlalchemy + fs           │
                       └──────────┬─────────────────────────────────┘
                                  │
                                  ▼
                       ┌────────────────────┐    ┌────────────┐
                       │  Postgres          │    │  Ollama    │
                       │  (configs,         │    │  (local    │
                       │   results)         │    │   LLM)     │
                       └────────────────────┘    └────────────┘
```

---

## 8. Inference engine (click → field type)

When the user clicks an element in the iframe, we POST `{element_outer_html, ancestor_chain, raw_text}` to `/infer`. The engine runs four checks in order, returns the first hit with a confidence score:

1. **Microdata / schema.org** — `itemprop`, `property`, `data-price`, `data-rating`, `aria-label` on element or nearest ancestor. Confidence: 0.95.
2. **Text pattern** — text against the regex library (price, percent, rating, date, url, email, currency). Confidence: 0.85.
3. **Label proximity** — preceding sibling text, `<label for>`, `<dt>/<dd>`, table header. Match label string against field synonyms (`price` ↔ `cost` ↔ `amount`). Confidence: 0.7.
4. **Local LLM** — only on miss. 1-shot prompt with element + 200 chars context. Confidence: 0.6.

If no signal hits, the popover shows "Couldn't auto-detect — pick a type" with the full dropdown.

**Field type library (v1 presets):**

| Type | Default regex (loose) | Default DQ | Typical attrs |
|---|---|---|---|
| `title` | — | non-empty, min 3 | h1, h2, `itemprop=name` |
| `price` | `[₹$€£]\s*[\d,]+(\.\d+)?` | parses as number > 0 | `itemprop=price`, `data-price` |
| `discount_pct` | `\d{1,2}\s*%` | 0–100 | `data-savings`, `.discount` |
| `image` | — (uses `src`/`srcset`) | resolves as URL | img tags |
| `rating` | `[0-5](\.\d)?` | 0–5 | `aria-label=rating`, `itemprop=ratingValue` |
| `review_count` | `[\d,]+` | parses as int ≥ 0 | `itemprop=reviewCount` |
| `description` | — | non-empty | p, `itemprop=description` |
| `availability` | `in stock\|out of stock\|...` | enum | `itemprop=availability` |
| `location` | — | non-empty | — |
| `date` | ISO + common formats | parses as date | time, `datetime=` |
| `url` | `https?://...` | parses as URL | a href |
| `custom` | user-supplied | user-supplied | — |

---

## 9. DQ engine

Per field, `dq = { required, regex, parses_as, min_len, max_len, range }`. The engine returns one of: `ok | empty | regex_fail | type_fail | range_fail | out_of_scope`.

**Item-level flagged ratio** = (# flagged fields) / (# total fields configured).

**Healing trigger (batch level):**
```
heal_batch  ⟺   (# items with flagged_ratio ≥ 0.5)  /  total_items  ≥  0.20
```
i.e. heal only when at least 20% of items have at least half their fields broken. Single bad items don't trigger healing — they just get marked partial.

**Healing guard (anti-loop):**
- Don't heal twice for the same `dom_skeleton_hash` within one batch.
- Don't auto-apply heal if the proposed v(n+1) still fails canary; surface to user.

---

## 10. LLM healing contract

**Input** (to local model via Ollama):
- Cleaned HTML of one representative failing file (scripts/styles/comments stripped, whitespace collapsed, capped at N tokens — chunk if needed).
- Current config (field names + types + previous selectors).
- List of failing fields with their DQ failure reasons.

**Prompt (sketch):**
```
You are rebuilding selectors for a page that has changed.

For each of these fields, return a robust XPath that targets the element
on the page. Prefer selectors using `id`, `data-*` attributes, `itemprop`,
or semantic class roots. Avoid positional indexes (e.g. div[3]/span[2]) —
they break easily.

Fields: title, price, discount_pct, rating
Previous (now broken) selectors: { ... }
Page HTML (cleaned): <...>

Return JSON: { "field_name": { "selector": "...", "selector_kind": "xpath" } }
```

**Post-check (in code, not LLM):**
1. Selector parses as valid XPath.
2. Selector resolves on the source file.
3. Resolved text passes the field's DQ rules.
4. Selector is not "too positional" — reject if it contains > 1 numeric index.
5. Run the proposed config against the next 2 files in the batch; both must pass canary DQ.

If any check fails for a field, keep the previous selector for that field and mark it as still-broken. Surface the diff to the user before applying.

---

## 11. Versioning

- Each accepted config bumps `version` by 1 within a domain.
- `latest` is the default for any new batch.
- Power user can pin a batch to a specific version via URL param or advanced UI.
- Version diff view (5.7) is the standard heal review surface.

---

## 12. Implementation phases

Small, demoable increments. Each phase ends with something a user can see in the browser.

| # | Phase | Demo at end of phase |
|---|---|---|
| 0 | Repo skeleton — FastAPI + Next.js boot, Postgres migration, Ollama smoke test | `/health` returns 200; `pnpm dev` renders a hello page |
| 1 | Upload + iframe render | Upload a .gz, see file 1 rendered in a sandboxed iframe; Prev/Next navigates files |
| 2 | Click-to-select + selector generation (no inference yet) | Click any element, get a stable selector in the side panel; named manually |
| 3 | Inference engine + presets library | Click a price, popover shows "Price (89%)" with auto-attached DQ |
| 4 | Parser + DQ engine | "Test on this file" runs the config, shows the canary result panel (5.5) |
| 5 | Batch parse + flagged ratio + result view | Upload 47 files, see the batch results panel (5.8) |
| 6 | LLM heal — propose & review | Drift screen (5.6) → review screen (5.7) → accept → re-run |
| 7 | Versioning UI + version diff + pin-to-version | Power-user view of v1/v2/v3 with diff |
| 8 | Advanced mode polish: raw JSON edit, custom XPath, custom DQ | Toggle Advanced, edit JSON, save |

Phases 0–5 are the MVP. 6 is the headline feature. 7–8 are quality-of-life for power users.

---

## 13. Open questions

1. **Local LLM model.** Default to `llama3.1:8b-instruct` via Ollama? Or `qwen2.5-coder:7b` (better at structured output)? Worth running both on a few real failure cases before locking in.
2. **HTML retention.** Keep raw HTML on disk forever, or evict after N days? Healing needs the original file to re-test, so at minimum keep until the next successful batch.
3. **List detection heuristic.** When the user clicks one item, we want to detect siblings. Algorithm: walk up to the nearest ancestor with ≥3 structurally similar children (same tag, similar class signature). Worth prototyping in phase 2 before phase 3.
4. **Output schema.** CSV columns = field names; nested fields (list scope) → one row per list item with a parent key? Or one row per file with JSON in cells? Probably the former for CSV, full nested JSON for the JSON export.
5. **Auth.** Single-user local for v1, but where do uploads land — `./uploads/{batch_id}/`?
6. **File size / batch size caps.** Need a sensible default before we hit memory issues. Suggest 500 files / 250MB unzipped per batch in v1, configurable.

I'll bring these back as concrete proposals once we start phase 0.
