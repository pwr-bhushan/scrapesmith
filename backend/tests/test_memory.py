"""Tests for spike.memory — DOM signature, similarity, retrieval, and the heal store.

Core contract:
  - paths(html) tokenises structure only: tag paths + attribute NAMES, never classes
  - a class_rename of a page must not change its signature at all
  - cosine() is idf-weighted, symmetric, 1.0 on self, 0.0 on disjoint
  - retrieve() returns <=k, best first, applying `exclude` before ranking
  - an entry is written only for anchor_correct AND status == "healed"
  - no entry ever contains an anchor value or raw HTML

All tests must FAIL (RED) until B2.1/B2.2 create spike/memory.py.
"""
from __future__ import annotations

import json
import re

import pytest

from spike.bench import BenchResult, load_case
from spike.memory import (
    build_entries,
    cosine,
    exclude_for,
    idf,
    load_store,
    paths,
    retrieve,
    save_store,
)

# ---------------------------------------------------------------------------
# Small hand-written pages. Same structure, every class value rewritten.
# ---------------------------------------------------------------------------

PAGE = """
<html><body><main>
  <div class="price-box"><span itemprop="price" data-price-amount="99">₹99</span></div>
  <div class="title-box"><h1 class="product-title">Widget</h1></div>
</main></body></html>
"""

PAGE_CLASS_RENAMED = """
<html><body><main>
  <div class="c0929-box"><span itemprop="price" data-price-amount="99">₹99</span></div>
  <div class="c48b1-box"><h1 class="c7425-title">Widget</h1></div>
</main></body></html>
"""

OTHER_PAGE = """
<html><body><article>
  <header><time datetime="2026-01-01">Jan</time></header>
  <p>text</p>
</article></body></html>
"""


def _entry(case_id, host, page_type, sig, field_name="price"):
    return {
        "case_id": case_id,
        "host": host,
        "page_type": page_type,
        "drift_type": "class_rename",
        "field_name": field_name,
        "field_type": "currency",
        "old_selector": "css=.old",
        "healed_selector": "css=[data-price-amount]",
        "signature": dict(sig),
    }


# ---------------------------------------------------------------------------
# paths() — the token design
# ---------------------------------------------------------------------------

class TestPathsTokenisation:
    def test_emits_root_to_leaf_tag_paths(self):
        toks = paths(PAGE)
        assert any(t.startswith("html>body>main>div>span") for t in toks), sorted(toks)

    def test_emits_attribute_names(self):
        toks = paths(PAGE)
        assert "@itemprop" in toks
        assert "@data-price-amount" in toks

    def test_class_rename_does_not_change_the_signature(self):
        """The reason classes are excluded from the token set.

        `class_rename` is one of the five drift transforms, and it rewrites *every* class
        in the page. A signature built on class names would therefore be maximally
        different exactly when the retriever most needs to recognise the page — it would
        retrieve on the one feature guaranteed not to survive the drift. Structure does
        survive it, so structure is what gets tokenised.
        """
        assert paths(PAGE) == paths(PAGE_CLASS_RENAMED)

    def test_no_class_value_appears_in_any_token(self):
        toks = paths(PAGE)
        for banned in ("price-box", "title-box", "product-title"):
            assert not any(banned in t for t in toks), f"{banned!r} leaked into {sorted(toks)}"

    def test_no_attribute_values_appear_in_any_token(self):
        """Names, not values: `@data-price-amount` yes, `99` no. Values are as
        redesign-fragile as classes, and carry page content we do not want stored."""
        toks = paths(PAGE)
        assert not any("99" in t for t in toks), sorted(toks)

    def test_structurally_different_pages_differ(self):
        assert paths(PAGE) != paths(OTHER_PAGE)

    def test_counter_semantics_repeated_structure_counts_up(self):
        one = paths("<html><body><ul><li>a</li></ul></body></html>")
        two = paths("<html><body><ul><li>a</li><li>b</li></ul></body></html>")
        key = "html>body>ul>li"
        assert two[key] == one[key] + 1


# ---------------------------------------------------------------------------
# cosine() / idf()
# ---------------------------------------------------------------------------

class TestSimilarity:
    def test_self_similarity_is_one(self):
        sig = paths(PAGE)
        store = [_entry("a", "h", "product", sig)]
        assert cosine(sig, sig, idf(store)) == pytest.approx(1.0)

    def test_disjoint_signatures_score_zero(self):
        a, b = {"x": 1}, {"y": 1}
        weights = idf([_entry("a", "h", "p", a), _entry("b", "h", "p", b)])
        assert cosine(a, b, weights) == pytest.approx(0.0)

    def test_is_symmetric(self):
        a, b = paths(PAGE), paths(OTHER_PAGE)
        weights = idf([_entry("a", "h", "p", a), _entry("b", "h", "p", b)])
        assert cosine(a, b, weights) == pytest.approx(cosine(b, a, weights))

    def test_rare_tokens_outweigh_ubiquitous_ones(self):
        """A token present in every entry carries no discriminative signal; idf must
        drive its weight toward zero so that sharing it does not look like similarity."""
        common = "html>body>div"
        store = [_entry(str(i), "h", "p", {common: 1, f"rare{i}": 1}) for i in range(5)]
        weights = idf(store)
        assert weights[common] < weights["rare0"]

    def test_empty_signature_scores_zero_not_error(self):
        assert cosine({}, paths(PAGE), idf([])) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# retrieve()
# ---------------------------------------------------------------------------

class TestRetrieve:
    def _store(self):
        return [
            _entry("product__class_rename", "shop.test", "product", paths(PAGE)),
            _entry("product__tag_swap", "shop.test", "product", paths(PAGE_CLASS_RENAMED)),
            _entry("article__combo", "news.test", "article", paths(OTHER_PAGE)),
        ]

    def test_returns_at_most_k(self):
        assert len(retrieve(paths(PAGE), self._store(), k=2)) == 2

    def test_k_zero_returns_nothing(self):
        assert retrieve(paths(PAGE), self._store(), k=0) == []

    def test_empty_store_returns_nothing(self):
        assert retrieve(paths(PAGE), [], k=3) == []

    def test_best_match_first(self):
        got = retrieve(paths(PAGE), self._store(), k=3)
        assert got[0]["page_type"] == "product"
        assert got[-1]["case_id"] == "article__combo"

    def test_k_larger_than_store_returns_whole_store(self):
        assert len(retrieve(paths(PAGE), self._store(), k=99)) == 3

    def test_exclude_filters_before_ranking(self):
        """Excluded entries must not merely be dropped from the output — if they were
        filtered after slicing to k, a self-match would silently shrink the result."""
        store = self._store()
        got = retrieve(paths(PAGE), store, k=2, exclude=lambda e: e["page_type"] == "product")
        assert [e["case_id"] for e in got] == ["article__combo"]

    def test_excluded_entries_do_not_weight_the_ranking(self):
        """The held-out page must not influence idf either. Under LOBO its own entries would
        push down the idf of exactly the tokens that identify it, so it steers the ranking it
        was excluded from — measured on the real 46-entry corpus, weighting by the full store
        moved the LOBO top-k on 5/21 cases at k=1 and 10/21 at k=5.

        Here: `<mark>` is unique to the query and to `twin`, so it should dominate. Padding the
        store with copies of a `<mark>`-bearing page that LOBO excludes drives its idf toward
        the floor; if idf came from the whole store, `decoy` would win on bulk instead.
        """
        query = "<html><body><main><mark>x</mark><span>y</span></main></body></html>"
        twin = "<html><body><main><mark>q</mark><em>z</em></main></body></html>"
        decoy = "<html><body><main><span>y</span><em>z</em></main></body></html>"
        held_out = "<html><body><main><mark>h</mark><mark>h</mark></main></body></html>"

        store = [
            _entry("other__a", "a.test", "a", paths(twin)),
            _entry("other__b", "b.test", "b", paths(decoy)),
            *[_entry(f"same__{i}", "s.test", "s", paths(held_out)) for i in range(8)],
        ]
        held = lambda e: e["case_id"].startswith("same__")  # noqa: E731
        got = retrieve(paths(query), store, k=1, exclude=held)
        assert got[0]["case_id"] == "other__a"


class TestPartitions:
    """LOO vs LOBO. Both are reported (decision 6) because they answer different
    questions: LOO measures retrieval when a sibling drift of the same page is in
    memory, LOBO measures it when nothing from that page is — the honest transfer number.
    """

    def _store(self):
        return [
            _entry("product__class_rename", "shop.test", "product", paths(PAGE)),
            _entry("product__tag_swap", "shop.test", "product", paths(PAGE)),
            _entry("product__combo", "shop.test", "product", paths(PAGE)),
            _entry("article__combo", "news.test", "article", paths(OTHER_PAGE)),
        ]

    def test_loo_excludes_only_the_same_case(self):
        case = load_case(str(__import__("pathlib").Path(__file__).parent.parent
                             / "fixtures" / "drift" / "product__combo"))
        keep = [e for e in self._store() if not exclude_for("loo", case)(e)]
        assert "product__combo" not in {e["case_id"] for e in keep}
        assert "product__tag_swap" in {e["case_id"] for e in keep}

    def test_lobo_excludes_every_variant_of_the_same_base_page(self):
        case = load_case(str(__import__("pathlib").Path(__file__).parent.parent
                             / "fixtures" / "drift" / "product__combo"))
        keep = [e for e in self._store() if not exclude_for("lobo", case)(e)]
        assert {e["case_id"] for e in keep} == {"article__combo"}

    def test_lobo_is_strictly_more_aggressive_than_loo(self):
        case = load_case(str(__import__("pathlib").Path(__file__).parent.parent
                             / "fixtures" / "drift" / "product__combo"))
        store = self._store()
        loo = [e for e in store if not exclude_for("loo", case)(e)]
        lobo = [e for e in store if not exclude_for("lobo", case)(e)]
        assert len(lobo) < len(loo)

    def test_unknown_partition_rejected(self):
        case = load_case(str(__import__("pathlib").Path(__file__).parent.parent
                             / "fixtures" / "drift" / "product__combo"))
        with pytest.raises(ValueError):
            exclude_for("everything", case)


# ---------------------------------------------------------------------------
# The store: what gets written, and what must never be
# ---------------------------------------------------------------------------

def _healed(case, field, selector="css=[data-price-amount]"):
    return BenchResult(
        provider_name="ollama/qwen2.5-coder:7b",
        case_id=case.case_id,
        field_name=field.name,
        proposed_selector=selector,
        resolved_values=[field.anchor],
        anchor=field.anchor,
        anchor_correct=True,
        resolve_but_wrong=False,
        dq_status="ok",
        drift_type=case.drift_type,
        status="healed",
    )


class TestEntryPopulationRule:
    def test_healed_and_anchor_correct_produces_an_entry(self, drift_dir):
        case = load_case(str(drift_dir / "product__combo"))
        entries = build_entries([_healed(case, case.fields[0])], [case])
        assert len(entries) == 1
        assert entries[0]["case_id"] == case.case_id
        assert entries[0]["field_name"] == case.fields[0].name

    def test_suspect_produces_no_entry(self, drift_dir):
        case = load_case(str(drift_dir / "product__combo"))
        r = _healed(case, case.fields[0])
        r.status = "suspect"
        assert build_entries([r], [case]) == []

    def test_still_broken_produces_no_entry(self, drift_dir):
        case = load_case(str(drift_dir / "product__combo"))
        r = _healed(case, case.fields[0])
        r.status = "still_broken"
        assert build_entries([r], [case]) == []

    def test_anchor_incorrect_produces_no_entry(self, drift_dir):
        """A gate verdict of `healed` is not sufficient on its own: the gate can only
        compare against the anchor when the anchor's page is in play. Memory must be
        built from the stronger signal, or it teaches the model its own mistakes."""
        case = load_case(str(drift_dir / "product__combo"))
        r = _healed(case, case.fields[0])
        r.anchor_correct = False
        assert build_entries([r], [case]) == []

    def test_entry_carries_the_page_signature(self, drift_dir):
        case = load_case(str(drift_dir / "product__combo"))
        entries = build_entries([_healed(case, case.fields[0])], [case])
        assert entries[0]["signature"] == dict(paths(case.after_html))


class TestNoLeakage:
    """The single most important property of the store.

    `build_prompt` deliberately never shows the model an anchor value. If an entry
    carried one, retrieving a same-site neighbour would hand the model the answer, and
    the k-sweep would be measuring leakage rather than transfer — the same failure the
    generic format example in prompt.py was written to avoid.
    """

    def test_no_entry_contains_any_corpus_anchor(self, drift_dir):
        cases, results, anchors = [], [], set()
        for case_dir in sorted(drift_dir.iterdir()):
            if not (case_dir / "case.json").is_file():
                continue
            case = load_case(str(case_dir))
            cases.append(case)
            for field in case.fields:
                anchors.add(field.anchor)
                results.append(_healed(case, field))

        entries = build_entries(results, cases)
        assert entries, "corpus produced no entries — test would pass vacuously"

        # Checked over the *textual* content of each entry: every string field, plus every
        # signature key. Signature values are element counts, and one corpus anchor is the
        # single character "7" — a bare substring scan over them reports a leak every time a
        # page has seven of some tag. Asserting they are ints is what licenses excluding them.
        for entry in entries:
            assert all(isinstance(v, int) for v in entry["signature"].values())
        blob = json.dumps(
            [{**e, "signature": sorted(e["signature"])} for e in entries], ensure_ascii=False
        )
        for anchor in anchors:
            assert anchor not in blob, f"anchor {anchor!r} leaked into the heal store"

    def test_no_entry_contains_raw_html(self, drift_dir):
        case = load_case(str(drift_dir / "product__combo"))
        entries = build_entries([_healed(case, f) for f in case.fields], [case])
        blob = json.dumps(entries, ensure_ascii=False)
        assert not re.search(r"<[a-zA-Z/!]", blob), "raw HTML leaked into the heal store"


class TestStoreRoundTrip:
    def test_jsonl_round_trip(self, tmp_path, drift_dir):
        case = load_case(str(drift_dir / "product__combo"))
        entries = build_entries([_healed(case, f) for f in case.fields], [case])
        path = tmp_path / "heal_memory.jsonl"
        save_store(path, entries)
        assert load_store(path) == entries

    def test_one_json_object_per_line(self, tmp_path, drift_dir):
        case = load_case(str(drift_dir / "product__combo"))
        entries = build_entries([_healed(case, f) for f in case.fields], [case])
        path = tmp_path / "heal_memory.jsonl"
        save_store(path, entries)
        lines = path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == len(entries)
        for line in lines:
            assert isinstance(json.loads(line), dict)

    def test_missing_store_loads_as_empty(self, tmp_path):
        """A k>0 run before any memory exists must degrade to k=0, not crash."""
        assert load_store(tmp_path / "nope.jsonl") == []
