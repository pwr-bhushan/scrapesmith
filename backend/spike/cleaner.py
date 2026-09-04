"""HTML cleaner for the heal spike.

clean_html(html, token_cap=None, chunk_hook=None) -> str
  - Strip <script>, <style>, <meta>, <link>, <noscript>, HTML comments
  - Strip attributes that cannot appear in a selector (href, src, style, on*, …)
  - Keep the tag tree, the selector-bearing attributes, and the text
  - Collapse whitespace
  - Preserve Unicode glyphs (₹, etc.)
  - If token_cap is set, call chunk_hook when truncating

ponytail: stdlib + bs4 only; no speculative abstraction.
"""
from __future__ import annotations

import re
from typing import Callable, Optional

from bs4 import BeautifulSoup, Comment

# Attributes a selector can actually target. Everything else (href, src, style, width,
# on*, framework noise) is dead weight in the prompt and gets dropped; `data-*` is kept
# by prefix because it is the second rung of the selector stability ladder.
_SELECTABLE_ATTRS = frozenset({"id", "class", "itemprop", "role", "aria-label"})


def clean_html(
    html: str,
    token_cap: Optional[int] = None,
    chunk_hook: Optional[Callable[[str, int], None]] = None,
) -> str:
    """Return cleaned HTML: the tag tree with only selector-bearing attributes and text.

    The consumer is a prompt asking a model to write a CSS/XPath selector, so both halves
    matter and neither is optional. Tags and attributes are what a selector is made of;
    the text is how the model tells which node holds the price when a redesign has
    renamed every class. Stripping either one leaves the model guessing.

    Args:
        html: Raw HTML string.
        token_cap: Approximate token limit (4 chars ≈ 1 token heuristic).
            When set and the cleaned markup exceeds the cap it is truncated and
            ``chunk_hook`` is called with ``(truncated_html, total_tokens)``
            before returning.
        chunk_hook: Optional callback invoked when the token cap fires.
            Signature: ``(text: str, estimated_tokens: int) -> None``.

    Returns:
        Cleaned markup suitable for passing to an LLM prompt.
    """
    soup = BeautifulSoup(html, "lxml")

    # Remove scripts, styles, comments, and head furniture that holds no selectable node
    for tag in soup.find_all(["script", "style", "meta", "link", "noscript"]):
        tag.decompose()
    for comment in soup.find_all(string=lambda s: isinstance(s, Comment)):
        comment.extract()
    for tag in soup.find_all(True):
        tag.attrs = {
            k: v
            for k, v in tag.attrs.items()
            if k in _SELECTABLE_ATTRS or k.startswith("data-")
        }

    # Serialize, preserve unicode; collapse internal whitespace
    text = soup.decode()
    # Collapse runs of whitespace to single space, strip
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n", "\n", text)
    text = text.strip()

    if token_cap is None:
        return text

    estimated = _estimate_tokens(text)
    if estimated <= token_cap:
        return text

    # Truncate to cap
    char_limit = token_cap * 4
    truncated = text[:char_limit]
    trunc_tokens = _estimate_tokens(truncated)
    if chunk_hook is not None:
        chunk_hook(truncated, trunc_tokens)
    return truncated


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: 1 token ≈ 4 characters."""
    return max(1, len(text) // 4)
