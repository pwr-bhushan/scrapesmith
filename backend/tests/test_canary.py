"""POST /parse/canary e2e: upload -> save config w/ anchor -> canary. pg + Playwright gated."""
import os
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.main import app
from tests._svc import url_reachable

pytestmark = [
    pytest.mark.skipif(not url_reachable(settings.database_url, 5432), reason="no postgres"),
    pytest.mark.skipif(os.environ.get("SKIP_PLAYWRIGHT") == "1", reason="SKIP_PLAYWRIGHT=1"),
]

PAGE = b"""<html><body><main>
  <h1 id="title">Widget Pro</h1>
  <span itemprop="price" class="price">1099</span>
</main></body></html>"""


async def test_canary_runs_config_and_checks_anchor():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        up = await c.post(
            "/upload",
            data={"host": f"{uuid.uuid4().hex}.com", "page_type": "product", "render_js": "false"},
            files={"file": ("p.html", PAGE, "text/html")},
        )
        batch_id = up.json()["batch_id"]
        await c.post(
            f"/batch/{batch_id}/config",
            json={
                "fields": [
                    {"name": "title", "selector": "css=#title", "scope": "single",
                     "dq": {"required": True, "parses_as": "text"},
                     "anchor": {"value": "Widget Pro"}},
                    {"name": "price", "selector": "css=[itemprop='price']", "scope": "single",
                     "dq": {"required": True, "parses_as": "number", "range": [0, None]},
                     "anchor": {"value": "1099"}},
                ]
            },
        )
        r = await c.post("/parse/canary", json={"batch_id": batch_id, "index": 0})

    body = r.json()
    assert body["data"]["title"] == "Widget Pro"
    assert body["field_status"] == {"title": "ok", "price": "ok"}
    assert body["anchor_ok"] == {"title": True, "price": True}
