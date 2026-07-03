"""Selector stability ladder (design §8.1). Pure candidate generation from an element descriptor;
uniqueness validation happens against the live DOM in app/pick.py.

A descriptor (from the overlay's JS) is a dict:
  {tag, id, classes[list], data{dict}, itemprop, role, landmark(css or None), nth_of_type(int)}
"""
from __future__ import annotations

import re

# stable class token: letters/hyphens only, length > 2 (skips utility/hash/1-2 char classes)
_STABLE_CLASS = re.compile(r"^[a-zA-Z]{3,}(?:-[a-zA-Z]+)*$")
# stable id: starts alpha, no digits (digits => generated like prod-8837), reasonable chars
_STABLE_ID = re.compile(r"^[A-Za-z][A-Za-z_-]*$")


def stable_id(value: str) -> bool:
    return bool(value) and bool(_STABLE_ID.match(value))


def stable_classes(classes) -> list:
    return [c for c in (classes or []) if _STABLE_CLASS.match(c)]


def _esc(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def single_candidates(desc: dict) -> list:
    """Ordered CSS candidates for a single element, most→least robust (§8.1)."""
    cands: list = []
    tag = desc.get("tag") or "*"
    landmark = desc.get("landmark")
    prefix = f"{landmark} " if landmark else ""

    # 1. id
    if stable_id(desc.get("id", "")):
        cands.append(f"#{_esc(desc['id'])}")

    # 2. data-* semantic attrs (valued first, then valueless)
    data = desc.get("data") or {}
    for k, v in data.items():
        if v and len(v) <= 40 and " " not in v:
            cands.append(f"[{k}='{_esc(v)}']")
    for k in data:
        cands.append(f"[{k}]")

    # 3. itemprop / role
    if desc.get("itemprop"):
        cands.append(f"[itemprop='{_esc(desc['itemprop'])}']")
    if desc.get("role"):
        cands.append(f"[role='{_esc(desc['role'])}']")

    # 4. stable class root under nearest landmark
    for c in stable_classes(desc.get("classes")):
        cands.append(f"{prefix}{tag}.{c}")

    # 5. structural fallback: one positional index, under landmark
    n = desc.get("nth_of_type")
    if isinstance(n, int) and n >= 1:
        cands.append(f"{prefix}{tag}:nth-of-type({n})")

    # de-dupe preserving order
    seen = set()
    out = []
    for c in cands:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def list_candidates(desc: dict, parent_selector: str) -> list:
    """Parent-relative CSS candidates for a list field (§8.2)."""
    tag = desc.get("tag") or "*"
    cands: list = []
    if desc.get("itemprop"):
        cands.append(f"{parent_selector} [itemprop='{_esc(desc['itemprop'])}']")
    for c in stable_classes(desc.get("classes")):
        cands.append(f"{parent_selector} {tag}.{c}")
    cands.append(f"{parent_selector} {tag}")

    seen = set()
    out = []
    for c in cands:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out
