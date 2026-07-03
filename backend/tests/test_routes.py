"""Upload + batch routes end-to-end. Postgres-gated; render route also Playwright-gated."""
import gzip
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

PAGE = b"<html><body><h1 class='product-title'>Widget</h1><span>9.99</span></body></html>"


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pg
async def test_upload_then_get_batch():
    async with _client() as c:
        resp = await c.post(
            "/upload",
            data={"host": "example.com", "page_type": "product", "render_js": "false"},
            files={"file": ("page.html.gz", gzip.compress(PAGE), "application/gzip")},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["file_count"] == 1
        batch_id = body["batch_id"]

        got = await c.get(f"/batch/{batch_id}")
        assert got.status_code == 200
        files = got.json()["files"]
        assert files[0]["index"] == 0
        assert files[0]["dom_skeleton_hash"]  # fingerprint computed


@pg
async def test_upload_rejects_oversize_gzip(monkeypatch):
    from app import upload as upmod

    monkeypatch.setattr(upmod, "MAX_FILE_BYTES", 5)
    async with _client() as c:
        resp = await c.post(
            "/upload",
            data={"host": "example.com", "page_type": "product"},
            files={"file": ("big.html.gz", gzip.compress(b"x" * 50), "application/gzip")},
        )
    assert resp.status_code == 400


@pg
async def test_get_missing_batch_404():
    async with _client() as c:
        resp = await c.get(f"/batch/{uuid.uuid4()}")
    assert resp.status_code == 404


@pg
@pytest.mark.skipif(os.environ.get("SKIP_PLAYWRIGHT") == "1", reason="SKIP_PLAYWRIGHT=1")
async def test_render_route_returns_snapshot():
    async with _client() as c:
        up = await c.post(
            "/upload",
            data={"host": "render.com", "page_type": "product", "render_js": "false"},
            files={"file": ("page.html", PAGE, "text/html")},
        )
        batch_id = up.json()["batch_id"]
        r = await c.get(f"/batch/{batch_id}/file/0/render")
    assert r.status_code == 200
    assert "data-scrapesmith-overlay" in r.text
