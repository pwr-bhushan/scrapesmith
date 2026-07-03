"""Heal: pure trigger/cluster/positional + post_check with a FakeProvider (Playwright-gated)."""
import os
import tempfile
from pathlib import Path

import pytest

from app.heal import cluster_failures, failing_fields, is_too_positional, post_check


def test_failing_fields_threshold():
    rates = {"price": {"failure_rate": 0.5}, "title": {"failure_rate": 0.1}}
    assert failing_fields(rates) == ["price"]


def test_is_too_positional():
    assert is_too_positional("css=div:nth-child(3)")
    assert is_too_positional("css=main div:nth-of-type(2) span:nth-of-type(4)")
    assert not is_too_positional("css=[data-price-amount]")
    assert not is_too_positional("css=main .price:nth-of-type(1)")


def test_cluster_by_skeleton():
    results = [
        {"dom_skeleton_hash": "h1", "field_status": {"price": "type_fail"}, "data": {}},
        {"dom_skeleton_hash": "h1", "field_status": {"price": "empty"}, "data": {}},
        {"dom_skeleton_hash": "h2", "field_status": {"price": "ok"}, "data": {}},
    ]
    clusters = cluster_failures(results, ["price"])
    assert len(clusters) == 1  # only h1 files fail
    assert clusters[0]["size"] == 2


# ---- post_check with a fake provider's proposals, against real rendered files ----

BEFORE = "<html><body><main><span class='old-price'>100</span></main></body></html>"
AFTER = "<html><body><main><span data-price='new'>100</span></main></body></html>"


@pytest.fixture()
def files():
    paths = []
    for html in (AFTER, AFTER):  # rep + 1 cluster file, both post-drift markup
        f = tempfile.NamedTemporaryFile("w", suffix=".html", delete=False)
        f.write(html)
        f.close()
        paths.append(f.name)
    yield paths
    for p in paths:
        Path(p).unlink(missing_ok=True)


@pytest.mark.skipif(os.environ.get("SKIP_PLAYWRIGHT") == "1", reason="SKIP_PLAYWRIGHT=1")
async def test_post_check_healed_vs_still_broken(files):
    rep, other = files
    fields_by_name = {
        "price": {
            "name": "price",
            "dq": {"required": True, "parses_as": "number"},
            "anchor": {"value": "100"},
        }
    }
    # a good proposal (resolves + DQ ok + anchor match) -> healed
    good = await post_check({"price": "css=[data-price]"}, rep, [other], fields_by_name, False)
    assert good["price"]["status"] == "healed"
    assert good["price"]["anchor_ok"] is True

    # a proposal that doesn't resolve -> still_broken
    bad = await post_check({"price": "css=.nope"}, rep, [other], fields_by_name, False)
    assert bad["price"]["status"] == "still_broken"

    # resolves + DQ ok but wrong value -> suspect (anchor diverges)
    fields_by_name["price"]["anchor"]["value"] = "999"
    suspect = await post_check({"price": "css=[data-price]"}, rep, [other], fields_by_name, False)
    assert suspect["price"]["status"] == "suspect"
    assert suspect["price"]["anchor_ok"] is False


# ---- route: propose (model unavailable) + accept -> new version. pg + Playwright gated. ----
import uuid as _uuid  # noqa: E402

from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.batch_parse import run_batch  # noqa: E402
from app.config import settings  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Job, UploadBatch  # noqa: E402
from app.storage import latest_config_version  # noqa: E402
from tests._svc import url_reachable  # noqa: E402

_gate = [
    pytest.mark.skipif(not url_reachable(settings.database_url, 5432), reason="no postgres"),
    pytest.mark.skipif(os.environ.get("SKIP_PLAYWRIGHT") == "1", reason="SKIP_PLAYWRIGHT=1"),
]

_PAGE = b"<html><body><main><h1 id='title'>X</h1></main></body></html>"


@pytest.mark.parametrize("_", [0])
@pytest.mark.skipif(not url_reachable(settings.database_url, 5432), reason="no postgres")
@pytest.mark.skipif(os.environ.get("SKIP_PLAYWRIGHT") == "1", reason="SKIP_PLAYWRIGHT=1")
async def test_heal_propose_unavailable_and_accept(_, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        up = await c.post(
            "/upload",
            data={"host": f"{_uuid.uuid4().hex}.com", "page_type": "product", "render_js": "false"},
            files={"file": ("p.html", _PAGE, "text/html")},
        )
        batch_id = up.json()["batch_id"]
        # a selector that will NOT resolve -> field fails on 100% of files (>=0.30 trigger)
        await c.post(
            f"/batch/{batch_id}/config",
            json={"fields": [{"name": "price", "selector": "css=.gone", "scope": "single",
                              "dq": {"required": True, "parses_as": "number"},
                              "anchor": {"value": "100"}}]},
        )
        async with SessionLocal() as s:
            batch = await s.get(UploadBatch, _uuid.UUID(batch_id))
            cv = await latest_config_version(s, batch.domain_id)
            job = Job(batch_id=_uuid.UUID(batch_id), kind="batch_parse", state="queued",
                      progress={"done": 0, "total": 1})
            s.add(job)
            await s.commit()
            await run_batch(s, job.id, _uuid.UUID(batch_id), cv)

        prop = (await c.post("/heal/propose", json={"batch_id": batch_id})).json()
        assert prop["triggered"] is True
        assert "price" in prop["failing"]
        assert prop["clusters"][0]["model"] == "unavailable"

        acc = (await c.post(
            "/heal/accept", json={"batch_id": batch_id, "accepted": {"price": "css=#title"}}
        )).json()
        assert acc["version"] == 2
        assert acc["healed"] == ["price"]
