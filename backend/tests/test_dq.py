"""Tests for spike.dq.check_dq().

Each DQ status must be reachable:
  ok | empty | regex_fail | type_fail | range_fail

All tests must FAIL (RED) until Step 3 implements check_dq().
"""
from __future__ import annotations

import pytest

from spike.dq import DQRule, check_dq


# ---------------------------------------------------------------------------
# Test: ok status
# ---------------------------------------------------------------------------

class TestDQOk:
    def test_valid_currency_value_returns_ok(self):
        """A valid currency value matching regex and parseable as number → ok."""
        rule = DQRule(
            required=True,
            regex=r"[₹$€]\s*[\d,]+",
            parses_as="number",
        )
        assert check_dq("₹1,49,900", rule) == "ok"

    def test_valid_text_no_constraints(self):
        """A non-empty text value with no extra constraints → ok."""
        rule = DQRule(required=True)
        assert check_dq("Apple MacBook Pro 14-inch", rule) == "ok"

    def test_optional_field_empty_is_ok(self):
        """An empty value on a non-required field → ok."""
        rule = DQRule(required=False)
        assert check_dq("", rule) == "ok"

    def test_optional_field_none_is_ok(self):
        """None on a non-required field → ok."""
        rule = DQRule(required=False)
        assert check_dq(None, rule) == "ok"

    def test_numeric_within_range(self):
        """A numeric value within [min_val, max_val] → ok."""
        rule = DQRule(
            required=True,
            parses_as="number",
            min_val=100.0,
            max_val=200000.0,
        )
        assert check_dq("149900", rule) == "ok"


# ---------------------------------------------------------------------------
# Test: empty status
# ---------------------------------------------------------------------------

class TestDQEmpty:
    def test_none_value_required_field(self):
        """None on a required field → empty."""
        rule = DQRule(required=True)
        assert check_dq(None, rule) == "empty"

    def test_empty_string_required_field(self):
        """Empty string on a required field → empty."""
        rule = DQRule(required=True)
        assert check_dq("", rule) == "empty"

    def test_whitespace_only_required_field(self):
        """Whitespace-only string on a required field → empty."""
        rule = DQRule(required=True)
        assert check_dq("   ", rule) == "empty"


# ---------------------------------------------------------------------------
# Test: regex_fail status
# ---------------------------------------------------------------------------

class TestDQRegexFail:
    def test_value_not_matching_regex(self):
        """Value that doesn't match the regex pattern → regex_fail."""
        rule = DQRule(
            required=True,
            regex=r"[₹$€]\s*[\d,]+",
        )
        assert check_dq("not-a-price", rule) == "regex_fail"

    def test_numeric_without_currency_symbol_fails_regex(self):
        """Plain number without currency symbol fails currency regex → regex_fail."""
        rule = DQRule(
            required=True,
            regex=r"[₹$€]\s*[\d,]+",
        )
        assert check_dq("149900", rule) == "regex_fail"


# ---------------------------------------------------------------------------
# Test: type_fail status
# ---------------------------------------------------------------------------

class TestDQTypeFail:
    def test_non_numeric_value_parses_as_number(self):
        """A non-numeric string when parses_as='number' → type_fail."""
        rule = DQRule(
            required=True,
            parses_as="number",
        )
        assert check_dq("not-a-number", rule) == "type_fail"

    def test_currency_value_with_glyph_fails_number_parse(self):
        """'₹1,49,900' when parses_as='number' without preprocessing → type_fail."""
        rule = DQRule(
            required=True,
            parses_as="number",
        )
        # Raw glyph-prefixed value cannot be parsed as bare float
        assert check_dq("₹1,49,900", rule) == "type_fail"


# ---------------------------------------------------------------------------
# Test: range_fail status
# ---------------------------------------------------------------------------

class TestDQRangeFail:
    def test_value_below_min(self):
        """Numeric value below min_val → range_fail."""
        rule = DQRule(
            required=True,
            parses_as="number",
            min_val=1000.0,
        )
        assert check_dq("50", rule) == "range_fail"

    def test_value_above_max(self):
        """Numeric value above max_val → range_fail."""
        rule = DQRule(
            required=True,
            parses_as="number",
            max_val=100.0,
        )
        assert check_dq("999", rule) == "range_fail"

    def test_value_at_boundary_is_ok(self):
        """Value exactly at min_val or max_val boundary → ok (inclusive)."""
        rule = DQRule(
            required=True,
            parses_as="number",
            min_val=100.0,
            max_val=200.0,
        )
        assert check_dq("100", rule) == "ok"
        assert check_dq("200", rule) == "ok"
