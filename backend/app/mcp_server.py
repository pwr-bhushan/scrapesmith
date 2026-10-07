"""MCP server: extraction jobs and heals for Claude Code and other agents (Section D).

A stdio process that talks to the running HTTP API — it holds no DB connection and re-validates
nothing the API already validates. Register with Claude Code:

    claude mcp add scrapesmith -- backend/.venv/bin/python -m app.mcp_server

``SCRAPESMITH_API_URL`` points it at the API (default http://localhost:8000).

Agents may apply a heal, but only one the gate marked ``healed`` (fork 3B): ``accept_heal`` takes
field *names*, and the selector comes from this process's own last ``propose_heal`` result, so an
agent cannot slip in a ``suspect`` or hand-written selector. Suspect heals stay a human call in
the UI. Every accept creates a new config version, so it can be pinned back.
"""
from __future__ import annotations

import io
import os
import zipfile
from pathlib import Path

import httpx
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

API_URL = os.environ.get("SCRAPESMITH_API_URL", "http://localhost:8000")
MAX_RESULT_ROWS = 200
# propose runs up to max_attempts model calls + Playwright gates per cluster
HEAL_TIMEOUT_S = 900.0
_HTML_EXT = (".html", ".htm")
_UPLOAD_EXT = (*_HTML_EXT, ".gz", ".zip")

mcp = MCPServer(
    "scrapesmith",
    instructions=(
        "Self-healing HTML extraction. Typical flow: list_batches (or upload_html) → "
        "start_parse → get_job until done → get_results. If a field's failure_rate is high, "
        "propose_heal, then accept_heal with the field names whose status is 'healed'."
    ),
)

# ponytail: process-local cache, fine for one stdio session; lost on restart, which only
# means propose_heal has to be called again
_proposals: dict[str, dict] = {}

# Refusals and API errors are raised as ToolError: mcp 2.x shows a ToolError's message to the
# agent but replaces any other exception's with a bare "Error executing tool", which would hide
# *why* an accept was refused.


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=API_URL)


async def _call(method: str, path: str, timeout: float = 60.0, **kwargs) -> dict:
    async with _client() as c:
        r = await c.request(method, path, timeout=timeout, **kwargs)
    if r.is_error:
        try:
            body = r.json()
        except ValueError:
            body = None
        detail = body.get("detail", r.text) if isinstance(body, dict) else r.text
        raise ToolError(f"{method} {path} → {r.status_code}: {detail}")
    return r.json()


@mcp.tool()
async def list_batches(limit: int = 20) -> dict:
    """Newest uploaded batches first, with host, page_type and file_count."""
    return await _call("GET", "/batches", params={"limit": limit})


@mcp.tool()
async def upload_html(path: str, host: str, page_type: str, render_js: bool = True) -> dict:
    """Upload HTML to a new batch. ``path`` is a .html/.htm/.gz/.zip file, or a directory whose
    .html/.htm files (recursively) are zipped and uploaded. ``host`` + ``page_type`` pick the
    domain whose saved config the batch will parse with."""
    p = Path(path).expanduser()
    if not p.exists():
        raise ToolError(f"{p} does not exist")
    if p.is_dir():
        name, data = f"{p.name or 'upload'}.zip", _zip_html(p)
    elif not p.name.lower().endswith(_UPLOAD_EXT):
        # the API stores any single file as HTML, so without this an agent could upload a key
        # or an env file into a batch and read it back
        raise ToolError(f"only .html/.htm/.gz/.zip files can be uploaded, not {p.name}")
    else:
        name, data = p.name, p.read_bytes()
    return await _call(
        "POST", "/upload",
        data={"host": host, "page_type": page_type, "render_js": str(render_js).lower()},
        files={"file": (name, data)},
    )


def _zip_html(root: Path) -> bytes:
    files = sorted(f for f in root.rglob("*") if f.is_file() and f.suffix.lower() in _HTML_EXT)
    if not files:
        raise ToolError(f"no .html/.htm files under {root}")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            zf.write(f, f.relative_to(root).as_posix())
    return buf.getvalue()


@mcp.tool()
async def start_parse(batch_id: str) -> dict:
    """Queue a background parse of every file in the batch. Returns a job_id for get_job."""
    return await _call("POST", "/parse/batch", json={"batch_id": batch_id})


@mcp.tool()
async def get_job(job_id: str) -> dict:
    """A parse job's state (queued | running | done | failed) and progress."""
    return await _call("GET", f"/jobs/{job_id}")


@mcp.tool()
async def get_results(batch_id: str, max_rows: int = 20) -> dict:
    """Per-field failure rates for the batch plus the first ``max_rows`` extracted rows
    (capped at 200; ``rows_total`` says how many exist)."""
    out = await _call("GET", f"/batch/{batch_id}/results")
    rows = out.get("rows", [])
    return out | {"rows": rows[: max(0, min(max_rows, MAX_RESULT_ROWS))],
                  "rows_total": len(rows)}


@mcp.tool()
async def propose_heal(batch_id: str, max_attempts: int = 3) -> dict:
    """Detect drifted fields, and for each failing layout cluster ask the model for new
    selectors, retrying up to ``max_attempts`` times. Each proposal has a status:
    healed (safe to accept), suspect (needs a human), still_broken. Applies nothing."""
    out = await _call("POST", "/heal/propose", timeout=HEAL_TIMEOUT_S,
                      json={"batch_id": batch_id, "max_attempts": max_attempts})
    _proposals[batch_id] = out
    return out


@mcp.tool()
async def accept_heal(batch_id: str, fields: list[str]) -> dict:
    """Apply the healed selectors for ``fields`` from this session's last propose_heal on the
    batch, creating a new config version. Refuses any field whose proposal is not 'healed'."""
    proposal = _proposals.get(batch_id)
    if proposal is None:
        raise ToolError(f"no proposal for batch {batch_id} in this session; call propose_heal")

    accepted, refused = {}, []
    for name in fields:
        verdicts = [cl["proposals"][name] for cl in proposal.get("clusters", [])
                    if name in cl["proposals"]]
        # The config holds one selector for every layout, so it has to be the same selector
        # and healed on each cluster that proposed it — not healed on one, suspect on another.
        statuses = sorted({v["status"] for v in verdicts}) or ["not proposed"]
        selectors = {v["selector"] for v in verdicts}
        if statuses != ["healed"]:
            refused.append(f"{name} ({'/'.join(statuses)})")
        elif len(selectors) > 1:
            refused.append(f"{name} (layouts healed with different selectors)")
        else:
            accepted[name] = selectors.pop()
    if refused:
        raise ToolError(
            "only 'healed' proposals can be accepted by an agent; review these in the UI: "
            + ", ".join(refused)
        )

    out = await _call("POST", "/heal/accept", json={
        "batch_id": batch_id, "accepted": accepted,
        "expected_version": proposal.get("config_version"),
    })
    _proposals.pop(batch_id, None)  # the config changed; that proposal is stale
    return out


if __name__ == "__main__":
    mcp.run()
