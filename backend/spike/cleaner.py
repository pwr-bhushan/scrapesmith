"""HTML cleaner for the heal spike.

clean_html(html, token_cap=None, chunk_hook=None) -> str
  - Strip <script>, <style>, HTML comments
  - Collapse whitespace
  - Preserve Unicode glyphs (₹, etc.)
  - If token_cap is set, call chunk_hook when truncating

ponytail: stdlib + bs4 only; no speculative abstraction.
"""
from __future__ import annotations

import re
from typing import Callable, Optional

from bs4 import BeautifulSoup, Comment


def clean_html(
    html: str,
    token_cap: Optional[int] = None,
    chunk_hook: Optional[Callable[[str, int], None]] = None,
) -> str:
    """Return cleaned HTML with scripts/styles/comments removed.

    Args:
        html: Raw HTML string.
        token_cap: Approximate token limit (4 chars ≈ 1 token heuristic).
            When set and the cleaned text exceeds the cap the text is
            truncated and ``chunk_hook`` is called with
            ``(truncated_text, total_tokens)`` before returning.
        chunk_hook: Optional callback invoked when the token cap fires.
            Signature: ``(text: str, estimated_tokens: int) -> None``.

    Returns:
        Cleaned text suitable for passing to an LLM prompt.
    """
    soup = BeautifulSoup(html, "lxml")

    # Remove scripts, styles, comments
    for tag in soup.find_all(["script", "style"]):
        tag.decompose()
    for comment in soup.find_all(string=lambda s: isinstance(s, Comment)):
        comment.extract()

    # Get text, preserve unicode; collapse internal whitespace
    text = soup.get_text(separator=" ")
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
