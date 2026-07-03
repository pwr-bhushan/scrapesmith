"""Batch aggregation (design §9): per-field failure rates + item flagged_ratio.

Input `results`: per-file dicts {"file": name, "field_status": {f: status}, "data": {...}}.
"""
from __future__ import annotations


def field_rates(results: list, fields: list) -> dict:
    """Per field: {failures, in_scope, failure_rate}. In scope = status != out_of_scope."""
    names = [f["name"] for f in fields]
    out = {}
    for name in names:
        in_scope = 0
        failures = 0
        for r in results:
            status = r["field_status"].get(name, "out_of_scope")
            if status == "out_of_scope":
                continue
            in_scope += 1
            if status != "ok":
                failures += 1
        rate = (failures / in_scope) if in_scope else 0.0
        out[name] = {"failures": failures, "in_scope": in_scope, "failure_rate": round(rate, 4)}
    return out


def flagged_ratios(results: list, fields: list) -> list:
    """Per file: fraction of in-scope fields not ok (item-level, for the results UI)."""
    names = [f["name"] for f in fields]
    ratios = []
    for r in results:
        scoped = [n for n in names if r["field_status"].get(n) != "out_of_scope"]
        flagged = [n for n in scoped if r["field_status"].get(n) != "ok"]
        ratio = (len(flagged) / len(scoped)) if scoped else 0.0
        ratios.append({"file": r.get("file"), "flagged_ratio": round(ratio, 4)})
    return ratios
