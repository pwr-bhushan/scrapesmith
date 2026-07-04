"""Version diff (pure) + advisory-lock concurrency + version/pin routes (pg-gated)."""
import asyncio
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.db import SessionLocal
from app.main import app
from app.storage import create_config_version, get_or_create_domain
from app.versioning import diff_fields
from tests._svc import url_reachable

pg = pytest.mark.skipif(not url_reachable(settings.database_url, 5432), reason="no postgres")


def test_diff_added_removed_changed():
    a = [{"name": "title", "selector": "css=#t", "type": "title", "scope": "single"},
         {"name": "price", "selector": "css=.old", "type": "price", "scope": "single"}]
    b = [{"name": "title", "selector": "css=#t", "type": "title", "scope": "single"},
         {"name": "price", "selector": "css=.new", "type": "price", "scope": "single"},
         {"name": "rating", "selector": "css=.r", "type": "rating", "scope": "single"}]
    d = diff_fields(a, b)
    assert d["added"] == ["rating"]
    assert d["removed"] == []
    assert d["changed"]["price"]["selector"] == ["css=.old", "css=.new"]


@pg
async def test_advisory_lock_serializes_concurrent_versions():
    # two concurrent create_config_version calls for the SAME domain must yield 1 and 2, not collide
    async with SessionLocal() as s0:
        domain = await get_or_create_domain(s0, f"{uuid.uuid4().hex}.com", "p", True)
        await s0.commit()
        domain_id = domain.id

    async def make():
        async with SessionLocal() as s:
            cv = await create_config_version(s, domain_id, [{"name": "x", "selector": "css=.x"}])
            await s.commit()
            return cv.version

    v1, v2 = await asyncio.gather(make(), make())
    assert sorted([v1, v2]) == [1, 2]


@pg
async def test_versions_diff_and_pin_routes():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        up = await c.post(
            "/upload",
            data={"host": f"{uuid.uuid4().hex}.com", "page_type": "p", "render_js": "false"},
            files={"file": ("p.html", b"<html><body><h1 id='t'>x</h1></body></html>", "text/html")},
        )
        batch_id = up.json()["batch_id"]
        domain_id = up.json()["domain_id"]

        await c.post(f"/batch/{batch_id}/config",
                     json={"fields": [{"name": "title", "selector": "css=#t", "scope": "single"}]})
        await c.post(
            f"/batch/{batch_id}/config",
            json={"fields": [{"name": "title", "selector": "css=#new", "scope": "single"}]},
        )

        vs = (await c.get(f"/domains/{domain_id}/versions")).json()["versions"]
        assert [v["version"] for v in vs] == [1, 2]

        d = (await c.get(f"/domains/{domain_id}/diff?a=1&b=2")).json()["diff"]
        assert d["changed"]["title"]["selector"] == ["css=#t", "css=#new"]

        pinned = (await c.post(f"/batch/{batch_id}/pin", json={"version": 1})).json()
        assert pinned["pinned_version"] == 1
