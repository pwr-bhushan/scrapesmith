# Phase 2 — Click-to-select + Stability Ladder + List Detection + /pick/validate + config v1

> Click an element in the rendered preview → a stable selector that **provably resolves**; "All N
> similar" detects the list; name the field; save config v1. Grounds: §8.1 ladder, §8.2 list
> detection, §5.2/5.3 UI, §6 ConfigField.

## Key architecture decision (recorded up front)

**Descriptor-based, server-validated.** The sandboxed iframe can't share a DOM with the parent, so:
1. Overlay (in the snapshot) captures the clicked element's **descriptor** in JS — `{tag, id,
   classes[], data{}, itemprop, role, landmark, nth_of_type}` — plus, for list scope, the detected
   **list-parent descriptor**. Attributes are script-independent, so they transfer cleanly from the
   sanitized snapshot to the raw page. `postMessage` → parent.
2. `POST /pick/validate` renders the **raw** file in Playwright, generates candidate selectors from
   the descriptor via the Python ladder (`app/selector.py`), and tests each with `locator().count()`
   — returning the first that uniquely resolves (single) or resolves ≥2 (list). This IS the §8.1
   round-trip parity check.
3. Structural fallback uses `:nth-of-type` (counts same-tag siblings → unaffected by script removal),
   never deep `nth-child` chains.

Rationale: ladder logic becomes pure, unit-testable Python; validation runs on the real extraction
DOM; no fragile absolute-path transfer between two different DOMs.

## Files

```
backend/app/
  selector.py   # ladder: single_candidates(desc), list_candidates(desc,parent), stable_id/class
  pick.py       # resolve_on_file(raw_path, css_selector, render_js) -> {count, values[]}
  routes/pick.py    # POST /pick/validate
  routes/config.py  # POST /batch/{id}/config (save v1), GET /batch/{id}/config
  render.py     # EXTEND overlay: click capture, descriptor, list detection (§8.2), postMessage
backend/tests/
  test_selector.py       # ladder ordering + stability rules (pure)
  test_pick_resolve.py   # resolve_on_file counts + values (playwright-gated)
  test_config_routes.py  # save/get config v1 (pg-gated)
frontend/
  components/RenderFrame.tsx  # EXTEND: listen for pick postMessage -> popover
  components/PickPopover.tsx  # value + scope toggle + name + Confirm (§5.3, minus ✨/inference)
  components/FieldPanel.tsx   # list of confirmed fields + Save config
  lib/api.ts                 # validatePick(), saveConfig(), getConfig()
```

## Ladder (§8.1), first uniquely-resolving wins

1. `#id` if id is stable (no digits, not generated)
2. `[data-*='v']` semantic data attrs (then valueless `[data-*]`)
3. `[itemprop='v']` / `[role='v']`
4. `{landmark} .{stable-class}` (alpha-only class under nearest landmark)
5. `{landmark} {tag}:nth-of-type(n)` structural fallback (≤1 positional index)

List (§8.2): overlay walks ancestors to nearest node with ≥3 children sharing tag + ≥60% stable-class
overlap = `list_parent_selector`; field selector becomes parent-relative; validate count ≥2.

## Scope / non-goals

- **In:** click→selector, uniqueness validation, list detection, manual field naming, save config v1.
- **Out (later):** inference/type auto-detect + presets (Phase 3), ✨ LLM (Phase 3), DQ + anchors
  (Phase 4), parsing/canary (Phase 4). Config v1 fields carry name+selector+scope only for now;
  type/dq/anchor added in later phases.
- Versioning is naive `max(version)+1`; advisory-lock is Phase 7.

## Steps: selector.py+tests → pick.py+tests → /pick/validate → config routes+tests → overlay JS → frontend → verify+commit.

## Security: overlay is still the only script (CSP unchanged); /pick/validate re-renders in the same
isolated egress-blocked context; selectors are validated, values are text only.
