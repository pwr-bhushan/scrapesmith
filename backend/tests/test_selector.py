"""Selector ladder ordering + stability rules (pure)."""
from app.selector import list_candidates, single_candidates, stable_classes, stable_id


def test_id_first_when_stable():
    desc = {"tag": "span", "id": "product-price", "classes": ["price"], "landmark": "main"}
    cands = single_candidates(desc)
    assert cands[0] == "#product-price"


def test_generated_id_skipped():
    assert not stable_id("prod-8837")  # digits => generated
    desc = {"tag": "div", "id": "prod-8837", "classes": ["product-title"], "landmark": "main"}
    cands = single_candidates(desc)
    assert all(not c.startswith("#") for c in cands)
    assert "main div.product-title" in cands


def test_ladder_order_data_then_itemprop_then_class():
    desc = {
        "tag": "span",
        "id": "",
        "data": {"data-price-amount": "149900"},
        "itemprop": "price",
        "classes": ["price"],
        "landmark": "main",
    }
    cands = single_candidates(desc)
    assert cands.index("[data-price-amount='149900']") < cands.index("[itemprop='price']")
    assert cands.index("[itemprop='price']") < cands.index("main span.price")


def test_structural_fallback_is_nth_of_type_and_last():
    desc = {"tag": "li", "classes": [], "landmark": "main", "nth_of_type": 3}
    cands = single_candidates(desc)
    assert cands[-1] == "main li:nth-of-type(3)"


def test_stable_classes_filters_utility_and_hash():
    assert stable_classes(["product-title", "css-1a2b3c", "x", "price"]) == [
        "product-title",
        "price",
    ]


def test_list_candidates_are_parent_relative():
    desc = {"tag": "span", "itemprop": "price", "classes": ["price"]}
    cands = list_candidates(desc, "main .product-card")
    assert cands[0] == "main .product-card [itemprop='price']"
    assert all(c.startswith("main .product-card ") for c in cands)
