"""Heal memory — DOM structure signatures, similarity, and the store of past heals.

Public API:
  paths(html) -> Counter[str]            structural signature of a page
  idf(store) -> dict[str, float]         inverse document frequency over stored signatures
  cosine(a, b, weights) -> float         idf-weighted cosine similarity
  retrieve(sig, store, k, exclude) -> list[dict]
  exclude_for(partition, case) -> callable    "loo" | "lobo" partition predicate
  build_entries(results, cases) -> list[dict]
  save_store(path, entries) / load_store(path)   artifacts/heal_memory.jsonl

The signature tokenises *structure only*: root→leaf tag paths plus attribute names.
Class values are deliberately absent — `class_rename` rewrites every class in the page,
so a class-based signature would differ most exactly when the retriever most needs to
recognise the page. Attribute values are absent for the same fragility reason, and
because they carry page content the store has no business keeping.

ponytail: stdlib + bs4; TF-IDF cosine over a jsonl file, no vector database.
"""
from __future__ import annotations

import json
import math
import pathlib
from collections import Counter
from typing import Any, Callable, Dict, Iterable, List, Mapping, Sequence

from bs4 import BeautifulSoup

PARTITIONS = ("loo", "lobo")


def paths(html: str) -> Counter:
    """Tokenise a page into its structural signature.

    Emits one token per element (its root→leaf tag path, e.g. ``html>body>main>div>span``)
    and one per attribute *name* (e.g. ``@itemprop``). Counts, not a set: a list page with
    twelve ``li`` is structurally unlike one with two.
    """
    soup = BeautifulSoup(html, "lxml")
    tokens: Counter = Counter()
    for el in soup.find_all(True):
        trail = [p.name for p in reversed(list(el.parents)) if p.name != "[document]"]
        tokens[">".join(trail + [el.name])] += 1
        for attr in el.attrs:
            tokens[f"@{attr}"] += 1
    return tokens


def idf(store: Sequence[Mapping[str, Any]]) -> Dict[str, float]:
    """Smoothed inverse document frequency of every token in the store.

    A token every page has (``html>body>div``) says nothing about which page this is;
    idf drives its weight down so that sharing it does not read as similarity.
    """
    n = len(store)
    df: Counter = Counter()
    for entry in store:
        df.update(set(entry.get("signature") or ()))
    return {tok: math.log((n + 1) / (d + 1)) + 1.0 for tok, d in df.items()}


def cosine(a: Mapping[str, int], b: Mapping[str, int], weights: Mapping[str, float]) -> float:
    """idf-weighted cosine similarity between two signatures. 0.0 when either is empty.

    A token in the query but in no stored signature is maximally discriminative, so it takes
    the df=0 value of the same smoothed formula ``idf()`` uses — not 1.0, which is that
    formula's *floor* and would weight the rarest token like the commonest one. Ranking is
    unaffected either way (such tokens only enter ``na``, which is constant across candidates
    within a call); the point is that the number means what the name says.
    """
    oov = max(weights.values(), default=1.0)

    def norm(sig: Mapping[str, int]) -> float:
        return math.sqrt(sum((v * weights.get(t, oov)) ** 2 for t, v in sig.items()))

    na, nb = norm(a), norm(b)
    if not na or not nb:
        return 0.0
    dot = sum(
        a[t] * b[t] * weights.get(t, oov) ** 2
        for t in (a.keys() & b.keys())
    )
    return dot / (na * nb)


def retrieve(
    signature: Mapping[str, int],
    store: Sequence[Mapping[str, Any]],
    k: int,
    exclude: Callable[[Mapping[str, Any]], bool] | None = None,
) -> List[Dict[str, Any]]:
    """Top-k structurally most similar past heals, best first.

    ``exclude`` is applied *before* ranking: filtering after slicing to k would silently
    return k−1 neighbours whenever a self-match ranked in.

    idf is computed over the *pool*, not the whole store, for the same reason. Under LOBO the
    held-out page must not contribute to any statistic that decides the ranking — its own
    entries would push down the idf of exactly the tokens that identify it. Measured on the
    46-entry corpus, weighting by the full store changed the LOBO top-k on 5/21 cases at k=1
    and 10/21 at k=5.

    ``k`` counts *entries*, not pages: the store holds one entry per healed field, and every
    entry from a page carries the same signature, so they tie and are emitted together. k=5
    shows ~2.5 distinct pages on this corpus. That is deliberate — the model is being shown
    old→healed pairs, and a page contributes as many as it repaired.
    """
    if k <= 0:
        return []
    pool = [e for e in store if not (exclude and exclude(e))]
    if not pool:
        return []
    weights = idf(pool)
    scored = sorted(
        pool,
        key=lambda e: cosine(signature, e.get("signature") or {}, weights),
        reverse=True,
    )
    return [dict(e) for e in scored[:k]]


def _base_page(case_id: str) -> str:
    """``product__combo`` → ``product``. Case ids are ``<base page>__<drift transform>``.

    ponytail: grouping is name-shaped, not content-shaped. A hand-written case that does not
    follow the convention forms its own LOBO group even if it is a variant of another page —
    `amazon_product` is one, and it shares anchors with the `product__*` family. Harmless
    here (its signature is 784 bytes against product's 3.2 KB, and neither retrieves the
    other in any arm); group on a `base_page` field in `case.json` if that stops being true.
    """
    return case_id.split("__")[0]


def exclude_for(partition: str, case: Any) -> Callable[[Mapping[str, Any]], bool]:
    """Predicate marking entries this case may not retrieve.

    ``loo``  — leave one case out: only the case itself.
    ``lobo`` — leave one base page out: every drift variant of the same base page.

    Both are reported. LOO answers "how well does memory work once a sibling drift of this
    page has been healed"; LOBO answers "does it transfer to a page never seen before" —
    the honest number, and the smaller one.
    """
    if partition not in PARTITIONS:
        raise ValueError(f"unknown partition {partition!r}; expected one of {PARTITIONS}")
    if partition == "loo":
        return lambda e: e.get("case_id") == case.case_id
    base = _base_page(case.case_id)
    return lambda e: _base_page(str(e.get("case_id", ""))) == base


def build_entries(
    results: Iterable[Any],
    cases: Sequence[Any],
) -> List[Dict[str, Any]]:
    """Turn bench results into memory entries — one per field that genuinely healed.

    The bar is ``anchor_correct AND status == "healed"``: the gate's verdict alone is not
    enough, because the gate can only compare against the anchor when the anchor's page is
    in play. Memory built from the weaker signal teaches the model its own mistakes.

    An entry carries structure and selectors, never an anchor value and never HTML — the
    prompt deliberately withholds the answer, and a retrieved neighbour must not hand it back.
    """
    by_id = {c.case_id: c for c in cases}
    signatures: Dict[str, Dict[str, int]] = {}
    entries: List[Dict[str, Any]] = []

    for r in results:
        if not (r.anchor_correct and r.status == "healed" and r.proposed_selector):
            continue
        case = by_id.get(r.case_id)
        if case is None:
            continue
        field = next((f for f in case.fields if f.name == r.field_name), None)
        if field is None:
            continue
        if case.case_id not in signatures:
            signatures[case.case_id] = dict(paths(case.after_html))
        entries.append({
            "case_id": case.case_id,
            "host": case.host,
            "page_type": case.page_type,
            "drift_type": case.drift_type,
            "field_name": field.name,
            "field_type": field.field_type,
            "old_selector": field.old_selector,
            "healed_selector": r.proposed_selector,
            "signature": signatures[case.case_id],
        })
    return entries


def save_store(path: str | pathlib.Path, entries: Sequence[Mapping[str, Any]]) -> None:
    """Write the store as jsonl — one entry per line, greppable and diffable.

    Overwrites: this is a snapshot of one run's successful heals, not an accumulator. The CLI
    refuses ``--save-memory`` on a k>0 or ``--case``-subset run for that reason — either would
    replace a full k=0 store with a partial or few-shot-assisted one.
    """
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in entries),
        encoding="utf-8",
    )


def load_store(path: str | pathlib.Path) -> List[Dict[str, Any]]:
    """Read the store. A missing file is an empty store, so a k>0 run before any memory
    exists degrades to k=0 rather than crashing."""
    p = pathlib.Path(path)
    if not p.is_file():
        return []
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
