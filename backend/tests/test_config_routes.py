"""Save/read config v1 + /pick/validate happy path. Postgres-gated (validate also Playwright)."""
import os
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.main import app
from tests._svc import url_reachable

pg = pytest.mark.skipif(
    not url_reachable(settings.database_url, 5432), reason="postgres not reachable"
)

PAGE = b"""<html><body><main>
  <h1 id="title">Widget</h1>
  <span itemprop="price" class="price">9.99</span>
</main></body></html>"""


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _upload(c, host: str = "") -> str:
    # unique host per test keeps config version numbering isolated across runs
    resp = await c.post(
        "/upload",
        data={
            "host": host or f"{uuid.uuid4().hex}.com",
            "page_type": "product",
            "render_js": "false",
        },
        files={"file": ("p.html", PAGE, "text/html")},
    )
    return resp.json()["batch_id"]


@pg
async def test_save_and_get_config_increments_version():
    async with _client() as c:
        batch_id = await _upload(c)
        fields = {"fields": [{"name": "title", "selector": "css=#title", "scope": "single"}]}
        r1 = await c.post(f"/batch/{batch_id}/config", json=fields)
        assert r1.status_code == 200
        assert r1.json()["version"] == 1

        got = await c.get(f"/batch/{batch_id}/config")
        assert got.json()["fields"][0]["name"] == "title"

        # second save for same domain -> version 2
        r2 = await c.post(f"/batch/{batch_id}/config", json=fields)
        assert r2.json()["version"] == 2


@pg
async def test_save_config_rejects_empty():
    async with _client() as c:
        batch_id = await _upload(c)
        r = await c.post(f"/batch/{batch_id}/config", json={"fields": []})
    assert r.status_code == 400


@pg
@pytest.mark.skipif(os.environ.get("SKIP_PLAYWRIGHT") == "1", reason="SKIP_PLAYWRIGHT=1")
async def test_pick_validate_generates_resolving_selector():
    async with _client() as c:
        batch_id = await _upload(c)
        r = await c.post(
            "/pick/validate",
            json={
                "batch_id": batch_id,
                "index": 0,
                "scope": "single",
                "descriptor": {
                    "tag": "span",
                    "id": "",
                    "itemprop": "price",
                    "classes": ["price"],
                    "landmark": "main",
                },
            },
        )
    body = r.json()
    assert body["resolves"] is True
    assert body["count"] == 1
    assert body["values"] == ["9.99"]
    assert "itemprop='price'" in body["selector"]
