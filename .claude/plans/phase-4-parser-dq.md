# Phase 4 — Parser + DQ engine + Anchors + Canary

> "Test on this file" runs the saved config in the browser context, shows the canary panel (5.5), and
> anchors are stored. Grounds: §9 DQ, §10 anchors, §5.5 canary.

## Pieces
- `app/dq.py` — `check_dq(value, dq, in_scope) -> ok|empty|regex_fail|type_fail|range_fail|out_of_scope`
  (ported/adapted from `spike/dq.py`, dict spec: required/regex/parses_as/min_len/max_len/range) +
  `normalize(value, kind)` for anchor comparison.
- `app/parser.py` — `parse_config(raw_path, fields, render_js) -> {data, field_status, flags}`.
  Renders once; per field resolves selector via `locator()`; single = first text, list = all texts;
  DQ per field (list: worst-of-items; parent count 0 = out_of_scope).
- `routes/parse.py` — `POST /parse/canary {batch_id, index}` → load latest config, parse, store a
  `parse_result` row, return panel + per-field anchor match.
- **Anchors (§10):** field config carries `anchor = {value, fingerprint}` captured at Confirm (the
  ValidateResult already returns the resolved value + we have the descriptor). Canary compares parsed
  value vs anchor (normalized) → `anchor_ok` per field.
- Frontend: `CanaryPanel` (5.5) — "Test on this file" → table of field / value / DQ status / anchor;
  "Re-pick" returns to the picker (already the same screen).

## Scope
- **In:** parser, DQ engine, anchor capture + canary anchor check, canary panel.
- **Out:** async batch (Phase 5), heal (Phase 6). Canary runs synchronously on one file.

## Steps: dq.py(+tests) → parser.py(+tests) → anchor on ConfigField → /parse/canary(+test) → CanaryPanel → verify+commit.
