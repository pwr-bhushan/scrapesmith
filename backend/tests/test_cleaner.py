"""Tests for spike.cleaner.clean_html().

All tests must FAIL (RED) until Step 3 implements clean_html().
"""
from __future__ import annotations

import pytest

from spike.cleaner import clean_html


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SCRIPT_HTML = """<!DOCTYPE html>
<html>
<head>
  <script>var x = 1; alert("xss");</script>
  <style>.price { color: red; }</style>
</head>
<body>
  <!-- This is a comment -->
  <div class="price">₹1,49,900</div>
  <a href="/product/123">View product</a>
  <p>Normal text content</p>
</body>
</html>"""

UNICODE_HTML = """<!DOCTYPE html>
<html><body>
  <span class="price">₹1,49,900</span>
  <span class="dollar">$99.99</span>
  <span class="euro">€199</span>
</body></html>"""

LARGE_HTML_TEMPLATE = """<!DOCTYPE html>
<html><body>{content}</body></html>"""


# ---------------------------------------------------------------------------
# Test: scripts are removed
# ---------------------------------------------------------------------------

class TestScriptRemoval:
    def test_script_tags_removed(self):
        """<script> blocks must not appear in cleaned output."""
        result = clean_html(SCRIPT_HTML)
        assert "<script>" not in result
        assert "alert(" not in result

    def test_script_content_removed(self):
        """Script content (var x = 1) must not appear in cleaned output."""
        result = clean_html(SCRIPT_HTML)
        assert "var x" not in result

    def test_style_tags_removed(self):
        """<style> blocks must not appear in cleaned output."""
        result = clean_html(SCRIPT_HTML)
        assert "<style>" not in result
        assert "color: red" not in result

    def test_html_comments_removed(self):
        """HTML comments must not appear in cleaned output."""
        result = clean_html(SCRIPT_HTML)
        assert "<!--" not in result
        assert "This is a comment" not in result


# ---------------------------------------------------------------------------
# Test: text content and anchor values survive
# ---------------------------------------------------------------------------

class TestContentPreservation:
    def test_price_text_survives(self):
        """The ₹1,49,900 price text must survive cleaning."""
        result = clean_html(SCRIPT_HTML)
        assert "1,49,900" in result

    def test_anchor_text_survives(self):
        """Anchor link text ('View product') must survive cleaning."""
        result = clean_html(SCRIPT_HTML)
        assert "View product" in result

    def test_paragraph_text_survives(self):
        """Normal paragraph text must survive cleaning."""
        result = clean_html(SCRIPT_HTML)
        assert "Normal text content" in result


# ---------------------------------------------------------------------------
# Test: Unicode / currency glyph preservation
# ---------------------------------------------------------------------------

class TestUnicodePreservation:
    def test_rupee_glyph_preserved(self):
        """The ₹ Unicode glyph must survive cleaning unchanged."""
        result = clean_html(UNICODE_HTML)
        assert "₹" in result

    def test_dollar_glyph_preserved(self):
        """The $ symbol must survive cleaning."""
        result = clean_html(UNICODE_HTML)
        assert "$" in result

    def test_euro_glyph_preserved(self):
        """The € symbol must survive cleaning."""
        result = clean_html(UNICODE_HTML)
        assert "€" in result

    def test_rupee_value_intact(self):
        """Full rupee value '₹1,49,900' must appear intact in cleaned output."""
        result = clean_html(UNICODE_HTML)
        assert "₹1,49,900" in result or "₹ 1,49,900" in result


# ---------------------------------------------------------------------------
# Test: token cap and chunk hook
# ---------------------------------------------------------------------------

class TestTokenCap:
    def test_no_token_cap_returns_full_text(self):
        """Without a token_cap, the full cleaned content is returned."""
        result = clean_html(SCRIPT_HTML)
        # At minimum the price and anchor text must be present
        assert "₹1,49,900" in result or "1,49,900" in result

    def test_token_cap_truncates_output(self):
        """With a very small token_cap, output must be shorter."""
        # Approx 4 chars per token; 10 tokens ≈ 40 chars
        long_content = "<p>" + ("word " * 1000) + "</p>"
        long_html = LARGE_HTML_TEMPLATE.format(content=long_content)
        result = clean_html(long_html, token_cap=10)
        # Estimated tokens of result must be ≤ cap (approx: len / 4)
        estimated = len(result) / 4
        assert estimated <= 10 + 5  # small allowance for rounding

    def test_chunk_hook_called_when_truncating(self):
        """chunk_hook must be invoked when token_cap causes truncation."""
        hook_calls = []

        def my_hook(text: str, estimated_tokens: int) -> None:
            hook_calls.append((text, estimated_tokens))

        long_content = "<p>" + ("word " * 1000) + "</p>"
        long_html = LARGE_HTML_TEMPLATE.format(content=long_content)
        clean_html(long_html, token_cap=10, chunk_hook=my_hook)

        assert len(hook_calls) == 1, "chunk_hook must be called exactly once"
        truncated_text, tok_count = hook_calls[0]
        assert isinstance(truncated_text, str)
        assert isinstance(tok_count, int)

    def test_chunk_hook_not_called_when_within_cap(self):
        """chunk_hook must NOT be called if content fits within token_cap."""
        hook_calls = []

        def my_hook(text: str, estimated_tokens: int) -> None:
            hook_calls.append((text, estimated_tokens))

        short_html = "<html><body><p>Hello</p></body></html>"
        clean_html(short_html, token_cap=1000, chunk_hook=my_hook)

        assert len(hook_calls) == 0, "chunk_hook must not be called when under cap"
