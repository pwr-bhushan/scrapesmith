"""run_batch + results/export routes (direct, no arq worker). pg + Playwright gated."""
import csv
import io
import os
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.batch_parse import gather_results, run_batch
from app.config import settings
from app.db import SessionLocal
from app.main import app
from app.models import Job, UploadBatch
from app.storage import latest_config_version
from tests._svc import url_reachable

pytestmark = [
    pytest.mark.skipif(not url_reachable(settings.database_url, 5432), reason="no postgres"),
    pytest.mark.skipif(os.environ.get("SKIP_PLAYWRIGHT") == "1", reason="SKIP_PLAYWRIGHT=1"),
]

PAGE = b"""<html><body><main>
  <h1 id="title">Widget</h1>
  <span itemprop="price" class="price">1099</span>
</main></body></html>"""


async def _setup(c) -> str:
    up = await c.post(
        "/upload",
        data={"host": f"{uuid.uuid4().hex}.com", "page_type": "product", "render_js": "false"},
        files={"file": ("p.html", PAGE, "text/html")},
    )
    batch_id = up.json()["batch_id"]
    await c.post(
        f"/batch/{batch_id}/config",
        json={"fields": [
            {"name": "title", "selector": "css=#title", "scope": "single",
             "dq": {"required": True, "parses_as": "text"}},
            {"name": "price", "selector": "css=[itemprop='price']", "scope": "single",
             "dq": {"required": True, "parses_as": "number"}},
        ]},
    )
    return batch_id


async def test_run_batch_then_results_and_export():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        batch_id = await _setup(c)

        # run the batch directly (bypassing arq)
        async with SessionLocal() as s:
            batch = await s.get(UploadBatch, uuid.UUID(batch_id))
            cv = await latest_config_version(s, batch.domain_id)
            job = Job(batch_id=uuid.UUID(batch_id), kind="batch_parse", state="queued",
                      progress={"done": 0, "total": 1})
            s.add(job)
            await s.commit()
            await run_batch(s, job.id, uuid.UUID(batch_id), cv)
            results = await gather_results(s, uuid.UUID(batch_id), cv.id)
            assert results[0]["data"]["title"] == "Widget"
            assert (await s.get(Job, job.id)).state == "done"

        # results aggregate
        res = (await c.get(f"/batch/{batch_id}/results")).json()
        assert res["field_rates"]["title"]["failure_rate"] == 0.0
        assert res["file_count"] == 1

        # csv export
        csv_text = (await c.get(f"/batch/{batch_id}/export.csv")).text
        rows = list(csv.reader(io.StringIO(csv_text)))
        assert rows[0][:2] == ["__file", "__item_index"]
        assert rows[1][2] == "Widget"

        # json export
        tree = (await c.get(f"/batch/{batch_id}/export.json")).json()
        assert tree["p.html"]["price"] == "1099"
