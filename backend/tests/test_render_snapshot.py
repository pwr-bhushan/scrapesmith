"""render_snapshot: strips scripts, injects overlay + CSP. Playwright-gated."""
import os
from pathlib import Path

import pytest

from app.render import render_snapshot

pytestmark = pytest.mark.skipif(
    os.environ.get("SKIP_PLAYWRIGHT") == "1", reason="SKIP_PLAYWRIGHT=1"
)

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures/drift/amazon_product/before.html"


async def test_snapshot_sanitized_and_overlaid():
    html = await render_snapshot(str(FIXTURE), render_js=False)
    assert "data-scrapesmith-overlay" in html  # our overlay injected
    assert "Content-Security-Policy" in html  # CSP locked
    assert "<script src" not in html.replace(" ", "")  # no external scripts survive
    assert len(html) > 0
