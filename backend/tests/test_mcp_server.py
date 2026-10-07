"""MCP server tools against a mocked HTTP API — the server is a thin client, so the tests pin
what it sends and what it refuses, not the API's behaviour (that has its own tests)."""
import io
import json
import zipfile

import httpx
import pytest
from mcp.server.mcpserver.exceptions import ToolError

import app.mcp_server as srv

PROPOSAL = {
    "triggered": True,
    "config_version": 4,
    "failing": ["price", "title"],
    "clusters": [
        {"hash": "h1", "size": 3, "model": "ollama/x", "attempts": 2, "proposals": {
            "price": {"selector": "css=.p", "status": "healed"},
            "title": {"selector": "css=.t", "status": "suspect"},
        }},
    ],
}


@pytest.fixture()
def api(monkeypatch):
    """Route every tool call to a handler; record requests so tests can assert on them."""
    sent = []
    replies = {}

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        key = f"{request.method} {request.url.path}"
        status, body = replies.get(key, (200, {}))
        return httpx.Response(status, json=body)

    monkeypatch.setattr(
        srv, "_client",
        lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://api"),
    )
    srv._proposals.clear()
    return sent, replies


async def test_accept_sends_only_healed_selectors(api):
    sent, replies = api
    replies["POST /heal/propose"] = (200, PROPOSAL)
    replies["POST /heal/accept"] = (200, {"version": 2, "healed": ["price"]})
    await srv.propose_heal("b1")
    out = await srv.accept_heal("b1", ["price"])
    assert out["version"] == 2
    assert json.loads(sent[-1].content) == {
        "batch_id": "b1", "accepted": {"price": "css=.p"}, "expected_version": 4,
    }


async def test_accept_refuses_a_suspect_field_and_sends_nothing(api):
    sent, replies = api
    replies["POST /heal/propose"] = (200, PROPOSAL)
    await srv.propose_heal("b1")
    with pytest.raises(ToolError, match="title.*suspect"):
        await srv.accept_heal("b1", ["price", "title"])
    assert [r.url.path for r in sent] == ["/heal/propose"]


async def test_accept_without_a_proposal_in_this_session_is_refused(api):
    with pytest.raises(ToolError, match="propose_heal"):
        await srv.accept_heal("b1", ["price"])


async def test_accept_clears_the_cached_proposal(api):
    """After an accept the config changed, so the old proposal is stale."""
    _, replies = api
    replies["POST /heal/propose"] = (200, PROPOSAL)
    await srv.propose_heal("b1")
    await srv.accept_heal("b1", ["price"])
    with pytest.raises(ToolError, match="propose_heal"):
        await srv.accept_heal("b1", ["price"])


async def test_results_rows_are_capped(api):
    _, replies = api
    replies["GET /batch/b1/results"] = (200, {"rows": [{"i": i} for i in range(50)],
                                              "field_rates": {}})
    out = await srv.get_results("b1", max_rows=5)
    assert len(out["rows"]) == 5 and out["rows_total"] == 50
    out = await srv.get_results("b1", max_rows=10_000)
    assert len(out["rows"]) == 50  # cap is a ceiling, not a target


async def test_api_errors_surface_the_detail(api):
    _, replies = api
    replies["POST /parse/batch"] = (400, {"detail": "no config saved for this domain"})
    with pytest.raises(ToolError, match="no config saved"):
        await srv.start_parse("b1")


async def test_upload_directory_zips_only_html(api, tmp_path):
    sent, replies = api
    replies["POST /upload"] = (200, {"batch_id": "b9", "file_count": 2})
    (tmp_path / "a.html").write_text("<html>a</html>")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.htm").write_text("<html>b</html>")
    (tmp_path / "notes.txt").write_text("skip me")
    out = await srv.upload_html(str(tmp_path), "shop.test", "product", render_js=False)
    assert out["batch_id"] == "b9"

    body = sent[-1].content
    start = body.index(b"PK\x03\x04")
    names = zipfile.ZipFile(io.BytesIO(body[start:])).namelist()
    assert sorted(names) == ["a.html", "sub/b.htm"]


async def test_upload_missing_path_is_refused(api, tmp_path):
    with pytest.raises(ToolError, match="does not exist"):
        await srv.upload_html(str(tmp_path / "nope"), "shop.test", "product")


async def test_upload_directory_without_html_is_refused(api, tmp_path):
    (tmp_path / "x.txt").write_text("no")
    with pytest.raises(ToolError, match="no .html"):
        await srv.upload_html(str(tmp_path), "shop.test", "product")


async def test_every_tool_is_registered():
    names = {t.name for t in await srv.mcp.list_tools()}
    assert names == {"list_batches", "upload_html", "start_parse", "get_job", "get_results",
                     "propose_heal", "accept_heal"}


async def test_refusal_reason_survives_the_mcp_layer(api):
    """mcp 2.x replaces a non-ToolError's message with a bare "Error executing tool", so an
    agent would see that accept was refused but not why. Found by the stdio smoke test."""
    with pytest.raises(ToolError, match="call propose_heal"):
        await srv.mcp.call_tool("accept_heal", {"batch_id": "b1", "fields": ["price"]})


async def test_accept_refuses_a_field_suspect_on_any_cluster(api):
    """Review fix: healed on a small layout but suspect on the largest one is not healed — the
    selector would be written to the config every layout parses with."""
    sent, replies = api
    two = {"triggered": True, "config_version": 4, "clusters": [
        {"proposals": {"price": {"selector": "css=.a", "status": "suspect"}}},
        {"proposals": {"price": {"selector": "css=.b", "status": "healed"}}},
    ]}
    replies["POST /heal/propose"] = (200, two)
    await srv.propose_heal("b1")
    with pytest.raises(ToolError, match="price.*suspect"):
        await srv.accept_heal("b1", ["price"])
    assert [r.url.path for r in sent] == ["/heal/propose"]


async def test_negative_max_rows_returns_no_rows(api):
    _, replies = api
    replies["GET /batch/b1/results"] = (200, {"rows": [{"i": i} for i in range(5)]})
    assert (await srv.get_results("b1", max_rows=-2))["rows"] == []


async def test_accept_refuses_layouts_that_healed_with_different_selectors(api):
    """The config holds one selector for every layout; cluster B's selector was never
    validated on cluster A's markup."""
    _, replies = api
    two = {"triggered": True, "config_version": 4, "clusters": [
        {"proposals": {"price": {"selector": "css=.a", "status": "healed"}}},
        {"proposals": {"price": {"selector": "css=.b", "status": "healed"}}},
    ]}
    replies["POST /heal/propose"] = (200, two)
    await srv.propose_heal("b1")
    with pytest.raises(ToolError, match="different selectors"):
        await srv.accept_heal("b1", ["price"])
