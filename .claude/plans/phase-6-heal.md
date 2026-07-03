# Phase 6 — Heal (cluster → propose → value-first review → accept)

> When a batch drifts, cluster the failing files, ask the model to rebuild the broken selectors,
> **prove the rebuild is anchor-correct** in code, show value diffs, and accept into a new config
> version. Grounds: §9 trigger/guards, §10 heal contract, §5.6/5.7 UI.

## Reuse
Spike heal interface (frozen, importable): `spike.heal.provider` (HealProvider, FieldSpec, Failure,
Proposal, validate_proposal), `spike.heal.{cloud,ollama}_provider`, `spike.cleaner.clean_html`.
**Anchor-correctness is enforced by the post-check (§10 step 5), not the prompt** — more robust, and
works even though the spike prompt predates anchors.

## Pieces
- `app/heal.py`:
  - `failing_fields(field_rates, threshold=0.30)` → names with rate ≥ threshold (§9 trigger).
  - `cluster_failures(results, failing)` → clusters keyed by `dom_skeleton_hash`, representative =
    centroid (most common hash's first file), + the cluster's files (§10 cluster-first).
  - `is_too_positional(selector)` → reject > 1 numeric index / deep nth-child (§10 step 4).
  - `post_check(proposals, rep_file, cluster_files, fields, render_js)` → per field:
    valid prefix → resolves → DQ → not-too-positional → **anchor check** → 2 more cluster files;
    status ∈ {healed, suspect, still_broken} + value + anchor_ok (§10 steps 1–6).
  - `select_provider()` → Cloud if `ANTHROPIC_API_KEY`, Ollama if `OLLAMA_HOST`, else None.
- `routes/heal.py`:
  - `POST /heal/propose {batch_id}` → trigger check, cluster, build FieldSpec/Failure + cleaned html
    + anchors, call provider.propose, post_check. Returns clusters + per-field proposal + value diff
    + status. **Never auto-applies.** If no provider: `model:"unavailable"` + the drift/clusters.
  - `POST /heal/accept {batch_id, accepted:{field:selector}}` → new config_version (created_by=
    `llm-heal`) merging accepted selectors into current config; bump version (naive; advisory-lock P7).
- Frontend: `HealReview` (5.6 drift + 5.7 value-first): failing fields, proposed value vs anchor,
  suspect flag, per-field accept → `/heal/accept`.

## Anti-loop (§9)
Cluster once per `dom_skeleton_hash`; `still_broken`/`suspect` fields are not auto-applied. Full
"don't re-heal a healed-and-failed hash" persistence is light for now (single propose call per batch).

## Test strategy
- `is_too_positional`, `failing_fields`, `cluster_failures` pure.
- `post_check` with a FakeProvider (returns known selectors) against crafted before/after html —
  asserts healed vs suspect vs still_broken (pg not needed; Playwright gated).
- `/heal/propose` returns `model:"unavailable"` path (no key) tested with pg.

## Steps: heal.py(+pure tests) → post_check(+playwright test) → routes(+test) → frontend → E2E+commit.
