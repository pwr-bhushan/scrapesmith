"""dom_skeleton_hash — a structural fingerprint for dedup/clustering (design §6 / §411).

Hash the tag tree only, with dynamic attributes stripped: drop id/data-* and any class token that
contains a digit or looks generated. Keep tag names, nesting/depth, `role`/`itemprop`, and stable
(alpha-only) class tokens. Goal: two structurally identical pages hash IDENTICALLY so failure
clustering (§10) and the anti-loop guard actually work.

This drives clustering, not extraction correctness — it is deliberately lossy.
"""
from __future__ import annotations

import hashlib
import re

from lxml import html as lxml_html

# keep these semantic attributes; their values are structural, not dynamic
_STABLE_ATTRS = ("role", "itemprop")
# a class token is "stable" if it is letters/hyphens only (no digits, no generated hashes)
_STABLE_CLASS = re.compile(r"^[a-zA-Z]+(?:-[a-zA-Z]+)*$")


def _stable_classes(value: str) -> list:
    return sorted(t for t in value.split() if _STABLE_CLASS.match(t))


def _node_repr(el) -> str:
    parts = [el.tag if isinstance(el.tag, str) else "_"]
    for attr in _STABLE_ATTRS:
        v = el.get(attr)
        if v:
            parts.append(f"{attr}={v}")
    classes = _stable_classes(el.get("class", ""))
    if classes:
        parts.append("class=" + ",".join(classes))
    head = "|".join(parts)
    children = "".join(
        _node_repr(c) for c in el.iterchildren() if isinstance(c.tag, str)
    )
    return f"({head}{children})"


def dom_skeleton_hash(html: str) -> str:
    """Return a stable 16-hex-char structural fingerprint of the HTML tag tree."""
    if not html or not html.strip():
        return hashlib.sha256(b"").hexdigest()[:16]
    tree = lxml_html.fromstring(html)
    return hashlib.sha256(_node_repr(tree).encode("utf-8")).hexdigest()[:16]
