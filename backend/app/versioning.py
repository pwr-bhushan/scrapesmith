"""Config version diff (design §11 / §5.7 advanced diff view). Pure."""
from __future__ import annotations


def _by_name(fields: list) -> dict:
    return {f["name"]: f for f in fields}


def diff_fields(fields_a: list, fields_b: list) -> dict:
    """Diff two config versions' field lists. Returns added/removed/changed(name->{key:[a,b]})."""
    a, b = _by_name(fields_a), _by_name(fields_b)
    added = sorted(set(b) - set(a))
    removed = sorted(set(a) - set(b))
    changed: dict = {}
    for name in sorted(set(a) & set(b)):
        deltas = {}
        for key in ("selector", "type", "scope", "list_parent_selector", "dq"):
            av, bv = a[name].get(key), b[name].get(key)
            if av != bv:
                deltas[key] = [av, bv]
        if deltas:
            changed[name] = deltas
    return {"added": added, "removed": removed, "changed": changed}
