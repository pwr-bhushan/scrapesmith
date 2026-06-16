"""Tests for spike.resolve — resolve_selector() and normalize().

All tests must FAIL (RED) until Step 3 implements the functions.

NOTE on Playwright: resolve_selector() uses Playwright sync against file://.
      The tests that call it are integration-level but run without network.
      playwright install chromium is required for those; they are skipped
      gracefully if playwright is not ready (SKIP_PLAYWRIGHT env var).
"""
from __future__ import annotations

import os
import pytest

from spike.resolve import normalize, resolve_selector


# ---------------------------------------------------------------------------
# Fixtures (inline HTML — no file I/O in these tests)
# ---------------------------------------------------------------------------

PRODUCT_HTML = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Product</title></head>
<body>
  <div id="product-detail">
    <h2 class="pdp-product-name">Apple MacBook Pro 14-inch</h2>
    <section class="pricing-section">
      <div class="price-container">
        <span class="a-price-whole"> ₹ 1,49,900 </span>
      </div>
    </section>
    <div class="review-summary">
      <em class="review-score">4.6</em>
    </div>
  </div>
</body>
</html>"""

# Mark Playwright tests so they can be skipped when Chromium is not installed
SKIP_PW = pytest.mark.skipif(
    os.environ.get("SKIP_PLAYWRIGHT") == "1",
    reason="SKIP_PLAYWRIGHT=1 — Chromium not installed",
)


# ---------------------------------------------------------------------------
# Test: resolve_selector — CSS selectors
# ---------------------------------------------------------------------------

class TestResolveSelectorCSS:
    @SKIP_PW
    def test_css_resolves_price(self):
        """css=.a-price-whole should resolve to the price text in after.html."""
        values = resolve_selector(PRODUCT_HTML, "css=.a-price-whole")
        assert len(values) >= 1
        # Value should contain the numeric part
        assert any("1,49,900" in v for v in values)

    @SKIP_PW
    def test_css_resolves_title(self):
        """css=.pdp-product-name should resolve to the product title."""
        values = resolve_selector(PRODUCT_HTML, "css=.pdp-product-name")
        assert len(values) >= 1
        assert any("MacBook" in v for v in values)

    @SKIP_PW
    def test_css_non_resolving_selector_returns_empty(self):
        """A CSS selector that matches nothing must return []."""
        values = resolve_selector(PRODUCT_HTML, "css=.does-not-exist-xyz")
        assert values == []

    @SKIP_PW
    def test_css_old_selector_fails_on_drifted_html(self):
        """The OLD selector (data-price-amount) must return [] on drifted HTML."""
        values = resolve_selector(PRODUCT_HTML, "css=[data-price-amount]")
        assert values == []


# ---------------------------------------------------------------------------
# Test: resolve_selector — XPath selectors
# ---------------------------------------------------------------------------

class TestResolveSelectorXPath:
    @SKIP_PW
    def test_xpath_resolves_price(self):
        """XPath selector resolves to price span."""
        values = resolve_selector(
            PRODUCT_HTML,
            "xpath=//span[@class='a-price-whole']",
        )
        assert len(values) >= 1
        assert any("1,49,900" in v for v in values)

    @SKIP_PW
    def test_xpath_non_resolving_returns_empty(self):
        """Non-matching XPath must return []."""
        values = resolve_selector(PRODUCT_HTML, "xpath=//span[@id='nonexistent']")
        assert values == []


# ---------------------------------------------------------------------------
# Test: resolve_selector — validation
# ---------------------------------------------------------------------------

class TestResolveSelectorValidation:
    def test_invalid_prefix_raises_value_error(self):
        """A selector without css= or xpath= prefix must raise ValueError."""
        with pytest.raises(ValueError, match="prefix"):
            resolve_selector(PRODUCT_HTML, ".price")

    def test_bare_xpath_without_prefix_raises_value_error(self):
        """An XPath expression without the xpath= prefix must raise ValueError."""
        with pytest.raises(ValueError, match="prefix"):
            resolve_selector(PRODUCT_HTML, "//span[@class='price']")


# ---------------------------------------------------------------------------
# Test: normalize() — currency
# ---------------------------------------------------------------------------

class TestNormalizeCurrency:
    def test_rupee_compact_vs_spaced(self):
        """'₹1,49,900' must normalize equal to ' ₹ 1,49,900 '."""
        assert normalize("₹1,49,900", "currency") == normalize(" ₹ 1,49,900 ", "currency")

    def test_rupee_leading_trailing_whitespace_stripped(self):
        """Leading/trailing whitespace must be stripped for currency."""
        assert normalize("  ₹1,49,900  ", "currency") == normalize("₹1,49,900", "currency")

    def test_thousands_separator_ignored(self):
        """Thousands commas must not affect equality for currency."""
        assert normalize("₹149900", "currency") == normalize("₹1,49,900", "currency")

    def test_internal_whitespace_collapsed(self):
        """Multiple spaces inside must collapse to one for currency."""
        assert normalize("₹   1,49,900", "currency") == normalize("₹1,49,900", "currency")


# ---------------------------------------------------------------------------
# Test: normalize() — number
# ---------------------------------------------------------------------------

class TestNormalizeNumber:
    def test_number_strips_commas(self):
        """Comma separators must be removed for number type."""
        assert normalize("1,234", "number") == normalize("1234", "number")

    def test_number_strips_whitespace(self):
        """Whitespace must be stripped for number type."""
        assert normalize("  42  ", "number") == normalize("42", "number")

    def test_number_collapses_internal_whitespace(self):
        """Internal whitespace must be collapsed for number type (e.g. '1 234' → '1234')."""
        assert normalize("1 234", "number") == "1234"


# ---------------------------------------------------------------------------
# Test: normalize() — text
# ---------------------------------------------------------------------------

class TestNormalizeText:
    def test_text_lowercased(self):
        """Text type must be lowercased."""
        assert normalize("Apple MacBook", "text") == normalize("apple macbook", "text")

    def test_text_whitespace_stripped(self):
        """Leading/trailing whitespace must be stripped for text."""
        assert normalize("  hello  ", "text") == normalize("hello", "text")

    def test_text_internal_space_collapsed(self):
        """Internal whitespace runs must collapse for text."""
        assert normalize("hello   world", "text") == normalize("hello world", "text")
