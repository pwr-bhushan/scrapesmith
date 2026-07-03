"""Parser runs a config against a rendered file. Playwright-gated."""
import os
import tempfile
from pathlib import Path

import pytest

from app.parser import parse_config

pytestmark = pytest.mark.skipif(
    os.environ.get("SKIP_PLAYWRIGHT") == "1", reason="SKIP_PLAYWRIGHT=1"
)

HTML = """<html><body><main>
  <h1 id="title">Widget Pro</h1>
  <span itemprop="price" class="price">1099</span>
  <ul class="cards">
    <li class="card"><span class="p">10</span></li>
    <li class="card"><span class="p">20</span></li>
    <li class="card"><span class="p">30</span></li>
  </ul>
</main></body></html>"""


@pytest.fixture()
def html_file():
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
        f.write(HTML)
        path = f.name
    yield path
    Path(path).unlink(missing_ok=True)


async def test_parse_single_and_list(html_file):
    fields = [
        {"name": "title", "selector": "#title", "scope": "single",
         "dq": {"required": True, "parses_as": "text"}},
        {"name": "price", "selector": "[itemprop='price']", "scope": "single",
         "dq": {"required": True, "parses_as": "number", "range": [0, None]}},
        {"name": "prices", "selector": "main .cards .p", "scope": "list",
         "dq": {"parses_as": "number"}},
    ]
    r = await parse_config(html_file, fields, render_js=False)
    assert r["data"]["title"] == "Widget Pro"
    assert r["data"]["price"] == "1099"
    assert r["data"]["prices"] == ["10", "20", "30"]
    assert r["field_status"] == {"title": "ok", "price": "ok", "prices": "ok"}
    assert r["flags"] == {}


async def test_missing_required_flags_empty(html_file):
    fields = [{"name": "missing", "selector": "#nope", "scope": "single",
               "dq": {"required": True}}]
    r = await parse_config(html_file, fields, render_js=False)
    assert r["data"]["missing"] is None
    assert r["field_status"]["missing"] == "empty"
    assert r["flags"]["missing"] == ["empty"]
