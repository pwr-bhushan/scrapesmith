"""Batch export (design §579): CSV one-row-per-list-item + nested JSON.

Input `results`: [{"file": name, "data": {field: value|[values]}}]; `fields` gives column order.
"""
from __future__ import annotations

import csv
import io


def _list_len(data: dict, list_fields: list) -> int:
    """Row count for a file = max length across its list fields, but always at least 1 row."""
    lengths = [len(data.get(f, []) or []) for f in list_fields if isinstance(data.get(f), list)]
    return max([*lengths, 1])


def csv_rows(results: list, fields: list) -> str:
    names = [f["name"] for f in fields]
    list_fields = [f["name"] for f in fields if f.get("scope") == "list"]
    header = ["__file", "__item_index", *names]

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(header)
    for r in results:
        data = r.get("data", {})
        n = _list_len(data, list_fields)
        for i in range(n):
            row = [r.get("file"), i]
            for name in names:
                val = data.get(name)
                if isinstance(val, list):
                    row.append(val[i] if i < len(val) else "")
                else:
                    row.append(val if val is not None else "")  # single-scope repeats across rows
            writer.writerow(row)
    return buf.getvalue()


def json_tree(results: list) -> dict:
    """{file: {field: value | [values]}}."""
    return {r.get("file"): r.get("data", {}) for r in results}
