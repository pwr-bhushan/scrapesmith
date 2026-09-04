"""Tests for spike.mutate — the labelled drift transforms behind the eval corpus.

The corpus is only worth measuring against if each transform does two things: breaks the
selector (otherwise there is nothing to heal and the rate is inflated) and preserves the
value (otherwise the anchor is unreachable and no proposal can ever be correct).
"""
from __future__ import annotations

import pytest
from bs4 import BeautifulSoup

from spike.mutate import DRIFT_TYPES, apply_drift, rename_class

HTML = (
    "<html><body><main id='wrap' data-page='pdp'>"
    "<div class='price-block'><span class='price-value' data-amount='9'>Rs 9</span></div>"
    "</main></body></html>"
)
BY_CLASS = "div.price-block > span.price-value"
BY_ATTR = "#wrap [data-amount]"


def select(html: str, selector: str) -> list:
    return BeautifulSoup(html, "html.parser").select(selector)


class TestValuePreservation:
    @pytest.mark.parametrize("drift", DRIFT_TYPES)
    def test_every_transform_preserves_the_value(self, drift):
        """No transform may touch text — the anchor has to survive the redesign."""
        assert "Rs 9" in apply_drift(HTML, drift, [BY_CLASS, BY_ATTR])


class TestSelectorBreakage:
    @pytest.mark.parametrize("drift", ["class_rename", "tag_swap", "wrapper_insert", "combo"])
    def test_structural_transforms_break_a_class_path(self, drift):
        after = apply_drift(HTML, drift, [BY_CLASS, BY_ATTR])
        assert not select(after, BY_CLASS)

    def test_attr_strip_breaks_an_attribute_selector(self):
        after = apply_drift(HTML, "attr_strip", [BY_CLASS, BY_ATTR])
        assert not select(after, BY_ATTR)

    def test_attr_strip_leaves_a_class_path_alone(self):
        """Not every transform breaks every selector shape — which is why the generator
        drops fields that did not actually drift instead of assuming they all did."""
        after = apply_drift(HTML, "attr_strip", [BY_CLASS, BY_ATTR])
        assert select(after, BY_CLASS)


class TestDeterminism:
    def test_same_input_gives_same_output(self):
        """A committed corpus must not move between regenerations, or the baseline
        number silently changes underneath the comparison it exists to support."""
        assert apply_drift(HTML, "combo", [BY_CLASS]) == apply_drift(HTML, "combo", [BY_CLASS])

    def test_rename_keeps_the_semantic_tail(self):
        assert rename_class("product-title").endswith("-title")
        assert rename_class("product-title") != "product-title"


class TestUnknownDrift:
    def test_unknown_drift_type_raises(self):
        with pytest.raises(ValueError, match="Unknown drift_type"):
            apply_drift(HTML, "reticulate_splines", [BY_CLASS])
