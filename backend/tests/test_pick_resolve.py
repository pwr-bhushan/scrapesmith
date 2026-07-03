"""resolve_many against a real rendered file. Playwright-gated."""
import os
import tempfile
from pathlib import Path

import pytest

from app.pick import resolve_many

pytestmark = pytest.mark.skipif(
    os.environ.get("SKIP_PLAYWRIGHT") == "1", reason="SKIP_PLAYWRIGHT=1"
)

HTML = """
<html><body><main>
  <ul class="cards">
    <li class="card"><span class="price">10</span></li>
    <li class="card"><span class="price">20</span></li>
    <li class="card"><span class="price">30</span></li>
  </ul>
  <h1 id="title">Widget</h1>
</main></body></html>
"""


@pytest.fixture()
def html_file():
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
        f.write(HTML)
        path = f.name
    yield path
    Path(path).unlink(missing_ok=True)


async def test_unique_and_list_counts(html_file):
    results = await resolve_many(
        html_file, ["#title", "main .cards .price", "main li.card"], render_js=False
    )
    by_sel = {r["selector"]: r for r in results}
    assert by_sel["#title"]["count"] == 1
    assert by_sel["#title"]["values"] == ["Widget"]
    assert by_sel["main .cards .price"]["count"] == 3  # list resolves to N
    assert by_sel["main li.card"]["count"] == 3


async def test_missing_selector_counts_zero(html_file):
    results = await resolve_many(html_file, [".nope"], render_js=False)
    assert results[0]["count"] == 0
