"""Minimal DQ (data quality) check subset for the heal spike.

Status values:
  ok           — value passes all configured rules
  empty        — value is None / empty string and field is required
  regex_fail   — value does not match the configured regex pattern
  type_fail    — value cannot be parsed as the declared type
  range_fail   — numeric value is outside the declared [min, max] range

Public API:
  DQStatus: Literal["ok", "empty", "regex_fail", "type_fail", "range_fail"]

  DQRule: dataclass with fields:
    required: bool = True
    regex: str | None = None
    parses_as: Literal["number", "text"] | None = None
    min_val: float | None = None
    max_val: float | None = None

  check_dq(value: str | None, rule: DQRule) -> DQStatus

ponytail: ordered guard clauses; no helper classes.

Number parsing semantics:
  - When regex is provided and passes (e.g. currency regex), the value is
    pre-cleaned (non-numeric chars stripped) before float() is attempted.
    This lets ₹1,49,900 pass parses_as=number when the regex already
    validated the currency format.
  - When no regex is present, only commas are stripped; a raw currency glyph
    (₹1,49,900) will produce type_fail as expected.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Optional

DQStatus = Literal["ok", "empty", "regex_fail", "type_fail", "range_fail"]


@dataclass
class DQRule:
    required: bool = True
    regex: Optional[str] = None
    parses_as: Optional[Literal["number", "text"]] = None
    min_val: Optional[float] = None
    max_val: Optional[float] = None


def check_dq(value: Optional[str], rule: DQRule) -> DQStatus:
    """Check a scraped value against DQ rules."""
    # 1. Empty check
    is_empty = value is None or str(value).strip() == ""
    if is_empty:
        return "empty" if rule.required else "ok"

    str_value = str(value).strip()

    # 2. Regex check — also determines how aggressively we clean for number parse
    regex_passed = False
    if rule.regex is not None:
        if not re.search(rule.regex, str_value):
            return "regex_fail"
        regex_passed = True

    # 3. Type check (parses_as)
    numeric: Optional[float] = None
    if rule.parses_as == "number":
        try:
            if regex_passed:
                # Regex already validated format (e.g. currency); strip all
                # non-numeric chars except decimal point and minus sign.
                cleaned = re.sub(r"[^\d.\-]", "", str_value)
            else:
                # No regex — only strip commas; a currency glyph causes type_fail
                cleaned = str_value.replace(",", "")
            numeric = float(cleaned)
        except (ValueError, TypeError):
            return "type_fail"

    # 4. Range check
    if rule.parses_as == "number" and numeric is not None:
        if rule.min_val is not None and numeric < rule.min_val:
            return "range_fail"
        if rule.max_val is not None and numeric > rule.max_val:
            return "range_fail"

    return "ok"
