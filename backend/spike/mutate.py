"""Labelled drift transforms — turn a page into a plausibly-redesigned version of itself.

Every eval case is a before/after pair of the *same* page. That is not a stylistic choice: the
§10 anchor check only means anything when the anchor's page is in the failing cluster (see B0b),
so `after.html` has to be `before.html` put through a transform that changes the markup and
leaves the values intact. A mutator gives that by construction.

The `drift_type` label is the point. One heal rate is a number; a rate per drift class says which
kinds of redesign the model survives, which is the axis heal memory is supposed to move.

  class_rename    every class renamed, structure untouched  (CSS-modules style rebuild)
  tag_swap        elements re-tagged, classes untouched     (h1→h2, span→div, semantic cleanup)
  wrapper_insert  a layout div wrapped around each target   (breaks `>` combinators)
  attr_strip      id and data-* removed                     (breaks the top rungs of the ladder)
  combo           all four at once                          (the honest worst case)

ponytail: BeautifulSoup (already a dep) + stdlib hashlib. No templating, no config file.
"""
from __future__ import annotations

import hashlib
import re
from typing import Callable, Dict, List

from bs4 import BeautifulSoup

DRIFT_TYPES = ("class_rename", "tag_swap", "wrapper_insert", "attr_strip", "combo")

# Realistic re-tagging: a redesign swaps elements for ones with the same box behaviour, so the
# page still renders. Nothing here changes what the text says.
_TAG_MAP = {
    "h1": "h2",
    "h2": "h3",
    "span": "div",
    "div": "section",
    "p": "div",
    "article": "section",
    "time": "span",
    "main": "section",
}

_WORD = re.compile(r"[a-z0-9]+", re.I)


def rename_class(name: str) -> str:
    """Deterministic class rename that keeps the trailing word.

    Real redesigns keep the *meaning* and change the prefix — `product-title` becomes something
    like `c8a3f-title`, not a random string. Keeping the tail is what makes this the *easy* end of
    the difficulty range: the model still has a semantic hint. `combo` removes the other hints.
    """
    tail = _WORD.findall(name)[-1] if _WORD.findall(name) else "el"
    digest = hashlib.md5(name.encode(), usedforsecurity=False).hexdigest()[:4]
    return f"c{digest}-{tail}"


def _class_rename(soup: BeautifulSoup, targets: List) -> None:
    for tag in soup.find_all(class_=True):
        tag["class"] = [rename_class(c) for c in tag.get("class", [])]


def _tag_swap(soup: BeautifulSoup, targets: List) -> None:
    # Snapshot first: renaming a tag while iterating find_all is fine, but building the list up
    # front keeps the traversal order stable run to run.
    for tag in list(soup.find_all(list(_TAG_MAP))):
        tag.name = _TAG_MAP[tag.name]


def _wrapper_insert(soup: BeautifulSoup, targets: List) -> None:
    # Only the field-bearing elements get wrapped. Wrapping everything would double the depth of
    # the whole document, which is not what a redesign looks like and would make the case
    # unrepresentative of anything.
    for tag in targets:
        wrapper = soup.new_tag("div")
        wrapper["class"] = ["layout-slot"]
        tag.wrap(wrapper)


def _attr_strip(soup: BeautifulSoup, targets: List) -> None:
    for tag in soup.find_all(True):
        tag.attrs = {
            k: v
            for k, v in tag.attrs.items()
            if k != "id" and not k.startswith("data-")
        }


_TRANSFORMS: Dict[str, Callable[[BeautifulSoup, List], None]] = {
    "class_rename": _class_rename,
    "tag_swap": _tag_swap,
    "wrapper_insert": _wrapper_insert,
    "attr_strip": _attr_strip,
}


def apply_drift(html: str, drift_type: str, selectors: List[str]) -> str:
    """Return `html` redesigned according to `drift_type`.

    Args:
        html: The before-page markup.
        drift_type: One of ``DRIFT_TYPES``.
        selectors: Bare CSS selectors (no ``css=`` prefix) naming the field-bearing elements.
            Used by ``wrapper_insert``, which only touches those; ignored by the others.

    Returns:
        The drifted markup.

    Raises:
        ValueError: If ``drift_type`` is not a known transform.
    """
    if drift_type not in DRIFT_TYPES:
        raise ValueError(f"Unknown drift_type {drift_type!r}; expected one of {DRIFT_TYPES}")

    soup = BeautifulSoup(html, "html.parser")
    targets = [el for sel in selectors for el in soup.select(sel)]

    # wrapper_insert must run before class_rename/attr_strip: it holds references to the target
    # elements, and the others rewrite the attributes those references were selected by.
    steps = ["wrapper_insert", "tag_swap", "class_rename", "attr_strip"] \
        if drift_type == "combo" else [drift_type]
    for step in steps:
        _TRANSFORMS[step](soup, targets)

    return soup.decode()


def demo() -> None:
    """Self-check: each transform breaks the selector shape it targets, and keeps the value.

    No transform breaks every selector shape — `attr_strip` leaves a class-based selector working,
    which is why the generator drops fields that did not actually drift instead of assuming they
    did. Each case below pairs a transform with a shape it is supposed to break.
    """
    html = (
        "<html><body><main id='wrap'><div class='price-block'>"
        "<span class='price-value' data-amount='9'>Rs 9</span>"
        "</div></main></body></html>"
    )
    by_class = "div.price-block > span.price-value"
    by_attr = "#wrap [data-amount]"
    cases = {
        "class_rename": by_class,
        "tag_swap": by_class,
        "wrapper_insert": by_class,
        "attr_strip": by_attr,
        "combo": by_class,
    }
    for sel in (by_class, by_attr):
        assert BeautifulSoup(html, "html.parser").select(sel), f"{sel} must match before"
    for drift, sel in cases.items():
        after = apply_drift(html, drift, [by_class, by_attr])
        soup = BeautifulSoup(after, "html.parser")
        assert not soup.select(sel), f"{drift} left {sel!r} working"
        assert "Rs 9" in after, f"{drift} destroyed the value"
    print(f"ok — {len(cases)} transforms break their target shape and preserve the value")


if __name__ == "__main__":
    demo()
