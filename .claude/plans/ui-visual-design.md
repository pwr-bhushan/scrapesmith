# Plan: Section C — UI visual design

**Created:** 2026-09-05
**Branch:** `dev`
**Depends on:** B2 complete and committed (`c5c39e7`, `9203af9`)
**Estimate:** ~12–14h

## Decisions locked 2026-09-05

The user chose all three from options presented with tradeoffs:

1. **Mechanism — Tailwind v4 + shadcn/ui.** Highest visual ceiling per hour, and the Radix
   primitives underneath give real focus-trap/keyboard nav in `PickPopover` rather than
   hand-written a11y. Accepted cost: goes from 3 runtime deps to ~8, and shadcn's default look is
   recognisable — mitigated by moving off the default neutral palette and radii (see §2).
2. **Direction — quiet developer tool.** Warm near-white canvas, one restrained accent, monospace
   for selectors and extracted values, borders over shadows. The rationale is load-bearing: the
   scraped page renders *inside* the app and brings its own loud colour (red price, green stock
   badge). App chrome has to recede so the user's data is what stands out.
3. **Depth — anchor the popover properly.** Uniform pass across all nine components *plus* fixing
   the picker's real defect and giving `HealReview` a before→after value diff.

## 0. Diagnosis — what is actually wrong

From `docs/img/01-click-to-pick.png` and the source. The frontend is 9 components / 924 lines with
**zero** `className`, 70 inline `style={{}}` objects, no stylesheet, and no CSS framework.

| symptom | cause | where |
|---|---|---|
| Every button is a raw browser default | no button styling anywhere | all 9 components |
| Content flush against the window edge, full-bleed | no page shell, no max-width, no centred column | `app/layout.tsx` is a bare `<body>` |
| Sections separated by bare `<hr>` rules | no card/panel primitive | `app/pick/[batchId]/page.tsx` |
| "Fields" rail cramped at the right edge, floats | `<div style={{minWidth: 260}}>` and nothing else | `FieldPanel.tsx:57` |
| Preview iframe ~85% dead space | fixed tall iframe, no fit-to-content | `RenderFrame.tsx` |
| App has no colour of its own | the only colour in the screenshot is the *scraped page's* | — |
| Popover is a bordered box stacked ~500px below the element clicked | it is rendered as a sibling of the iframe, not anchored | `RenderFrame.tsx` renders `<PickPopover>` after `<iframe>` |

**Most of that is layout, not components.** The shell + two-column split + card treatment is ~2h
and would have been needed under any of the four options considered.

### The one non-obvious finding

Anchoring the popover is **not** a CSS change. The injected picker script at
`backend/app/render.py:104-109` posts `{type, descriptor, text, listParent}` — no geometry. The
parent window has no idea where in the iframe the click happened. This needs:

- `render.py`: add the clicked element's `getBoundingClientRect()` to the postMessage payload.
- `RenderFrame.tsx`: add the iframe's own offset, then position the popover against that.
- `tests/test_render_snapshot.py` / `test_render_smoke.py` assert on the injected script — check
  both before touching it.

Scroll position inside the iframe matters too: the rect is viewport-relative, so the popover has to
either re-anchor on iframe scroll or be captured at click time and pinned. **Pinned at click time**
is the lazy correct answer — the popover is modal-ish in practice and the user is not scrolling
while deciding a field name.

## 1. Phases

### C0 — Setup (~1h)
- Tailwind v4 via `@tailwindcss/postcss`, `app/globals.css` with `@import "tailwindcss"` and the
  token block as `@theme`.
- `components.json` + shadcn init. Pull only what is used: `button`, `input`, `select`, `dialog`,
  `popover`, `table`, `badge`, `card`, `separator`, `tabs`. Nothing speculative.
- `lucide-react` for icons — replaces the `✕ ✓ ✨ ◀ ▶` glyphs currently inline in JSX.

### C2 — Tokens (~30min)
Defined once in `@theme`, referenced everywhere. Concrete values so this is not re-litigated:

```
--color-canvas:   #fbfaf9   warm near-white page
--color-surface:  #ffffff   cards, panels
--color-border:   #e7e5e1
--color-ink:      #1a1a19
--color-muted:    #6b6b68
--color-accent:   #2f5d50   deep green — buttons, focus rings, active states
--color-ok:       #2f6f4e
--color-warn:     #8a6d1f
--color-danger:   #9b3232
--radius:         8px
font-sans:        system stack
font-mono:        ui-monospace — selectors, extracted values, anchors
```

Deliberately *not* shadcn's default `zinc` + `0.5rem`: that combination is the recognisable
"shadcn app" look and the whole point of choosing a direction was to not have it.

### C3 — Shell and layout (~2h) — the biggest single win
- `app/layout.tsx`: real `<body>` with canvas background, font vars, and an app header carrying
  the product name plus `host · config vN` context.
- Centred `max-w-[1400px]` container with consistent page padding.
- `app/pick/[batchId]/page.tsx`: replace the flat stack of five components + `<hr>`s with a
  two-column grid — preview left, sticky fields rail right — and cards for Batch results / Heal
  review / Versions below.
- Preview iframe: size to content rather than a fixed tall box.

### C4 — Component conversion (~4h)
All nine, inline styles → Tailwind + the shadcn primitives. `UploadForm`, `RenderFrame`,
`FieldPanel`, `CanaryPanel`, `BatchResults`, `HealReview`, `VersionPanel`, `AdvancedPanel`,
`PickPopover`. Tables get real header/row treatment; DQ statuses and heal verdicts (`healed` /
`suspect` / `still_broken`) become `Badge` variants rather than coloured text.

### C5 — Popover anchoring (~2h)
Per §0. `render.py` payload gains `rect`, `PickPopover` renders in a Radix `Popover` anchored to a
virtual element at the captured coordinates. Keyboard: Esc cancels, Enter confirms when the name is
non-empty and the selector resolves.

### C6 — Heal review before→after (~1.5h)
`HealReview` currently lists proposals. Give it the diff the product's whole argument rests on: old
selector → new selector, and more importantly **old value → new value** with the anchor match state
called out. This is the screen that demonstrates "you review values, not selectors".

### C7 — Re-shoot screenshots (~1h)
All four in `docs/img/` are stale the moment C3 lands. They are at README lines 22–27, above the
fold — the first thing anyone sees. Re-shoot with the same script/flow used originally.

## 2. Constraints

- **Backend is frozen except `render.py`'s injected script.** No route, model or parser changes.
- `npm run typecheck && npm run build` must pass; the backend suite (235) must stay green because
  C5 touches `render.py`.
- Do not restyle the *rendered page* inside the iframe — that is the user's untrusted content and
  the sandbox/CSP treatment around it is a security property (§14), not a style choice.

## 3. Risks

| risk | mitigation |
|---|---|
| shadcn default look defeats the point of choosing a direction | tokens set in C2 *before* any component is pulled; no component ships with default `zinc` |
| `render.py` change breaks the two render tests | read both tests before editing; they assert on injected-script content |
| Tailwind class strings make currently-readable components noisy | extract repeated clusters to the shadcn primitive, not to `@apply` |
| Restyle drifts into behaviour changes | C4 is styling only; the one behavioural change is C5's anchoring, isolated in its own phase |
| Screenshots re-shot before the UI settles | C7 last, after typecheck+build pass |
