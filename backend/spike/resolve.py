"""Selector resolution engine for the heal spike.

Uses Playwright sync API against file:// URIs so the resolution engine
matches the production source of truth.

Public API:
  resolve_selector(html: str, selector: str) -> list[str]
      selector must be prefixed "css=…" or "xpath=…"
      Returns list of extracted text values; [] if nothing resolves.

  normalize(value: str, field_type: str) -> str
      Normalise a scraped value for anchor-equality comparison.
      field_type: "currency" | "number" | "text"
      Rules:
        - Strip leading/trailing whitespace
        - Collapse internal whitespace runs to single space
        - For currency/number: strip thousands separators, unify currency
          symbol spacing so "₹1,49,900" == " ₹ 1,49,900 "
        - For text: lowercase

ponytail: Playwright sync + tempfile; normalize is pure string ops.
"""
from __future__ import annotations

import os
import re
import tempfile
from typing import List

_VALID_PREFIXES = ("css=", "xpath=")


def resolve_selector(html: str, selector: str) -> List[str]:
    """Resolve a CSS or XPath selector against an HTML string.

    Uses Playwright sync API with a ``file://`` URI (temp file).

    Args:
        html: Full HTML document string.
        selector: Prefixed selector, e.g. ``"css=.price"`` or
            ``"xpath=//span[@class='price']"``.

    Returns:
        List of text content strings for matching nodes.
        Empty list if the selector matches nothing or is unparseable.

    Raises:
        ValueError: If ``selector`` is not prefixed with ``css=`` or
            ``xpath=``.
    """
    if not selector.startswith(_VALID_PREFIXES):
        raise ValueError(
            f"Selector must have a css= or xpath= prefix, got: {selector!r}"
        )

    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright

    # Write HTML to a temp file so Playwright can load it as file://
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".html", delete=False, encoding="utf-8"
    ) as f:
        f.write(html)
        tmp_path = f.name

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page()
            page.goto(f"file://{tmp_path}")
            try:
                locator = page.locator(selector)
                count = locator.count()
                values = []
                for i in range(count):
                    text = locator.nth(i).inner_text()
                    values.append(text)
            except PlaywrightError:
                values = []
            browser.close()
        return values
    finally:
        os.unlink(tmp_path)


def normalize(value: str, field_type: str = "text") -> str:
    """Normalise a scraped value for anchor-equality comparison.

    Args:
        value: Raw extracted string.
        field_type: One of ``"currency"``, ``"number"``, ``"text"``.

    Returns:
        Normalised string suitable for ``==`` comparison.
    """
    # Strip outer whitespace
    s = value.strip()

    if field_type == "currency":
        # Remove thousands separators (commas)
        s = s.replace(",", "")
        # Collapse all whitespace (including around currency symbol)
        s = re.sub(r"\s+", "", s)
        return s

    if field_type == "number":
        # Remove thousands commas and collapse all whitespace (e.g. "1 234" → "1234")
        s = re.sub(r"\s+", "", s.replace(",", ""))
        return s

    # text (default)
    s = s.lower()
    # Collapse internal whitespace
    s = re.sub(r"\s+", " ", s)
    return s
