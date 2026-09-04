"""DQ engine (design §9). Dict-based spec so it reads config JSON directly.

Statuses: ok | empty | regex_fail | type_fail | range_fail | out_of_scope
dq spec keys: required(bool), regex(str), parses_as('number'|'text'|'url'),
              min_len(int), max_len(int), range([min,max])

Number-cleaning semantics ported from spike/dq.py: if a regex is present and passes, strip all
non-numeric chars before float(); otherwise only strip commas (so a bare currency glyph type_fails).
"""
from __future__ import annotations

import re

STATUSES = ("ok", "empty", "regex_fail", "type_fail", "range_fail", "out_of_scope")

_URL_RE = re.compile(r"^https?://\S+$")


def check_dq(value: str | None, dq: dict | None, in_scope: bool = True) -> str:
    dq = dq or {}
    if not in_scope:
        return "out_of_scope"

    is_empty = value is None or str(value).strip() == ""
    if is_empty:
        return "empty" if dq.get("required") else "ok"

    s = str(value).strip()

    regex = dq.get("regex")
    regex_passed = False
    if regex:
        if not re.search(regex, s):
            return "regex_fail"
        regex_passed = True

    min_len, max_len = dq.get("min_len"), dq.get("max_len")
    if min_len is not None and len(s) < min_len:
        return "range_fail"
    if max_len is not None and len(s) > max_len:
        return "range_fail"

    parses_as = dq.get("parses_as")
    if parses_as == "number":
        cleaned = re.sub(r"[^\d.\-]", "", s) if regex_passed else s.replace(",", "")
        try:
            numeric = float(cleaned)
        except (ValueError, TypeError):
            return "type_fail"
        rng = dq.get("range")
        if rng:
            lo, hi = rng[0], rng[1]
            if lo is not None and numeric < lo:
                return "range_fail"
            if hi is not None and numeric > hi:
                return "range_fail"
    elif parses_as == "url":
        if not _URL_RE.match(s):
            return "type_fail"

    return "ok"


def normalize(value: str | None, kind: str = "text") -> str:
    """Canonical form for anchor comparison (§10)."""
    if value is None:
        return ""
    s = str(value).strip()
    if kind == "number":
        return re.sub(r"[^\d.\-]", "", s)
    return re.sub(r"\s+", " ", s)
