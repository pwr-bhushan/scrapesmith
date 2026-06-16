"""Tests for HealProvider ABC and validate_proposal().

Tests verify:
  1. HealProvider ABC cannot be instantiated directly.
  2. Concrete subclass must implement propose(cleaned_html, fields, failures).
  3. FakeProvider returns canned selectors.
  4. validate_proposal() rejects/excludes bad output:
     - Missing keys (field name absent from raw dict) → excluded
     - Non-prefixed selectors (no css= / xpath=) → excluded with warning
  5. validate_proposal() normalises valid proposals into Proposal objects.

All tests must FAIL (RED) until Step 3 implements validate_proposal().
FakeProvider is defined inline here — it's test-only and needs no implementation.
"""
from __future__ import annotations

import inspect
import pytest

from spike.heal.provider import (
    Failure,
    FieldSpec,
    HealProvider,
    Proposal,
    validate_proposal,
)


# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

SAMPLE_FIELDS = [
    FieldSpec(name="price", field_type="currency", old_selector="css=[data-price-amount]"),
    FieldSpec(name="title", field_type="text", old_selector="css=.product-title"),
]

SAMPLE_FAILURES = [
    Failure(field_name="price", dq_status="empty"),
    Failure(field_name="title", dq_status="empty"),
]

CLEANED_HTML = "<div class='a-price-whole'>₹1,49,900</div><h2 class='pdp-product-name'>MacBook</h2>"


# ---------------------------------------------------------------------------
# FakeProvider — canned responses, no network/model
# ---------------------------------------------------------------------------

class FakeProvider(HealProvider):
    """Test double: returns preset selectors for known fields."""

    CANNED = {
        "price": "css=.a-price-whole",
        "title": "css=.pdp-product-name",
    }

    def propose(
        self,
        cleaned_html: str,
        fields,
        failures,
    ):
        return {
            f.field_name: Proposal(selector=self.CANNED[f.field_name])
            for f in failures
            if f.field_name in self.CANNED
        }


# ---------------------------------------------------------------------------
# Test: ABC enforcement
# ---------------------------------------------------------------------------

class TestHealProviderABC:
    def test_cannot_instantiate_abstract_class(self):
        """HealProvider must be abstract and not directly instantiable."""
        with pytest.raises(TypeError):
            HealProvider()  # type: ignore[abstract]

    def test_propose_is_abstract_method(self):
        """propose must be declared as an abstract method on HealProvider."""
        assert getattr(HealProvider.propose, "__isabstractmethod__", False), (
            "HealProvider.propose must be declared with @abc.abstractmethod"
        )

    def test_propose_signature(self):
        """propose must accept (self, cleaned_html, fields, failures)."""
        sig = inspect.signature(HealProvider.propose)
        params = list(sig.parameters.keys())
        assert "cleaned_html" in params
        assert "fields" in params
        assert "failures" in params


# ---------------------------------------------------------------------------
# Test: FakeProvider (concrete implementation)
# ---------------------------------------------------------------------------

class TestFakeProvider:
    def test_fake_provider_instantiates(self):
        """FakeProvider (concrete subclass) must instantiate without error."""
        provider = FakeProvider()
        assert provider is not None

    def test_fake_provider_returns_canned_selectors(self):
        """FakeProvider must return the canned selector for each failure."""
        provider = FakeProvider()
        result = provider.propose(CLEANED_HTML, SAMPLE_FIELDS, SAMPLE_FAILURES)
        assert "price" in result
        assert result["price"].selector == "css=.a-price-whole"
        assert "title" in result
        assert result["title"].selector == "css=.pdp-product-name"

    def test_fake_provider_result_type(self):
        """FakeProvider must return dict[str, Proposal]."""
        provider = FakeProvider()
        result = provider.propose(CLEANED_HTML, SAMPLE_FIELDS, SAMPLE_FAILURES)
        for key, val in result.items():
            assert isinstance(key, str)
            assert isinstance(val, Proposal)


# ---------------------------------------------------------------------------
# Test: validate_proposal() — valid output
# ---------------------------------------------------------------------------

class TestValidateProposalValid:
    def test_valid_css_selector_accepted(self):
        """A raw selector prefixed with css= must be accepted and wrapped in Proposal."""
        raw = {"price": "css=.a-price-whole", "title": "css=.pdp-product-name"}
        result = validate_proposal(raw, SAMPLE_FAILURES)
        assert "price" in result
        assert isinstance(result["price"], Proposal)
        assert result["price"].selector == "css=.a-price-whole"

    def test_valid_xpath_selector_accepted(self):
        """A raw selector prefixed with xpath= must be accepted."""
        raw = {"price": "xpath=//span[@class='a-price-whole']"}
        failures = [Failure(field_name="price", dq_status="empty")]
        result = validate_proposal(raw, failures)
        assert "price" in result
        assert result["price"].selector == "xpath=//span[@class='a-price-whole']"


# ---------------------------------------------------------------------------
# Test: validate_proposal() — missing key excluded
# ---------------------------------------------------------------------------

class TestValidateProposalMissingKey:
    def test_missing_field_excluded_from_result(self):
        """A field in failures but absent from raw dict must not appear in result."""
        raw = {"price": "css=.a-price-whole"}  # title is missing
        result = validate_proposal(raw, SAMPLE_FAILURES)
        # price should be present, title should be absent
        assert "price" in result
        assert "title" not in result

    def test_completely_empty_raw_gives_empty_result(self):
        """If raw is empty dict, result must be empty dict."""
        result = validate_proposal({}, SAMPLE_FAILURES)
        assert result == {}


# ---------------------------------------------------------------------------
# Test: validate_proposal() — non-prefixed selector excluded
# ---------------------------------------------------------------------------

class TestValidateProposalBadSelector:
    def test_bare_css_selector_excluded(self):
        """A selector without css= or xpath= prefix must be excluded from result."""
        raw = {"price": ".a-price-whole"}  # no css= prefix
        failures = [Failure(field_name="price", dq_status="empty")]
        result = validate_proposal(raw, failures)
        assert "price" not in result

    def test_bare_xpath_excluded(self):
        """An XPath expression without xpath= prefix must be excluded."""
        raw = {"price": "//span[@class='price']"}  # no xpath= prefix
        failures = [Failure(field_name="price", dq_status="empty")]
        result = validate_proposal(raw, failures)
        assert "price" not in result

    def test_mixed_valid_and_invalid_only_valid_returned(self):
        """When one field has a bad selector and another is valid, only valid is returned."""
        raw = {
            "price": "css=.a-price-whole",  # valid
            "title": ".pdp-product-name",   # invalid (no prefix)
        }
        result = validate_proposal(raw, SAMPLE_FAILURES)
        assert "price" in result
        assert "title" not in result
