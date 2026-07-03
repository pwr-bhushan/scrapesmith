# Phase 3 — Inference Engine + Presets + opt-in LLM

> Click an element → "Looks like: PRICE (89%)" with a default DQ preset; ✨ asks the model only on
> demand. Grounds: §8 inference tiers, §8.2 preset library.

## Cascade (§8), first hit wins

1. **Structured data** — `itemprop`/`data-*` name maps to a type; (JSON-LD value match = stretch,
   deferred). Confidence 0.95.
2. **Text regex** — element text vs the preset regex library (price/currency, percent, rating,
   review_count, date, url, email, availability). Confidence 0.85.
3. **Label proximity** — a supplied label/near-text hint matched against preset synonyms
   (price↔cost↔amount). Confidence 0.70.
4. **LLM classifier** — opt-in only (✨). Uses Anthropic if `ANTHROPIC_API_KEY` set, else returns
   `source="llm_unavailable"` (honest — models aren't wired yet). Confidence 0.60.

No hit → `{type: null, confidence: 0, source: "none"}` → popover shows "pick a type".

## Files
- `app/presets.py` — FIELD_PRESETS: type → {regex, dq(default), synonyms, itemprop_names}.
- `app/infer.py` — `infer_type(text, itemprop, data, label) -> {type, confidence, source}`;
  `classify_with_llm(...)` gated on key.
- `routes/infer.py` — `POST /infer` {text, itemprop?, data?, label?, use_llm?}.
- Frontend: `PickPopover` calls `/infer` on open, shows type + confidence + a "Change ⌄" preset
  dropdown + ✨ button; confirmed field carries `type` + preset `dq`.
- `lib/api.ts` — `infer()`.

## Scope
- **In:** deterministic tiers 1–3, preset library w/ default DQ (data only), popover type UI, ✨ plumbing.
- **Out:** DQ *evaluation* engine + anchors (Phase 4), JSON-LD value-matching, parsing.
- Presets attach a default `dq` object to the field config; the engine that runs it is Phase 4.

## Steps: presets.py → infer.py (+tests) → /infer route (+test) → popover wiring → verify+commit.
