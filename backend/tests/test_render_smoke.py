"""Phase 0.5 smoke: render a fixture HTML file headless via the Playwright pool.

Gated on SKIP_PLAYWRIGHT (mirrors the spike convention).
"""
import os
from pathlib import Path

import pytest

from app.render import render_file

pytestmark = pytest.mark.skipif(
    os.environ.get("SKIP_PLAYWRIGHT") == "1", reason="SKIP_PLAYWRIGHT=1"
)

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures/drift/amazon_product/before.html"


async def test_render_fixture():
    assert FIXTURE.exists(), FIXTURE
    result = await render_file(str(FIXTURE))
    assert result["text_len"] > 0
