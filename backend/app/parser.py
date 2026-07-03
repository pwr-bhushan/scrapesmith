"""Generic parser: run a config's fields against a rendered file (design §4/§9).

Returns {data, field_status, flags}. data holds a value (single) or list (list scope). Each field is
DQ-checked; flags carries the reason for any non-ok status.
"""
from __future__ import annotations

from pathlib import Path

from playwright.async_api import async_playwright

from app.dq import check_dq
from app.render import _block_egress

_MAX_LIST = 500


async def parse_config(raw_path: str, fields: list, render_js: bool) -> dict:
    url = Path(raw_path).resolve().as_uri()
    data: dict = {}
    field_status: dict = {}
    flags: dict = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context(java_script_enabled=render_js)
            page = await context.new_page()
            await page.route("**/*", _block_egress)
            await page.goto(url)

            for f in fields:
                name = f["name"]
                dq = f.get("dq") or {}
                try:
                    loc = page.locator(f["selector"])
                    count = await loc.count()
                except Exception:
                    count = 0

                if f.get("scope") == "list":
                    values = []
                    for i in range(min(count, _MAX_LIST)):
                        values.append((await loc.nth(i).inner_text()).strip())
                    data[name] = values
                    if count == 0:
                        status = "out_of_scope"
                    else:
                        statuses = [check_dq(v, dq) for v in values]
                        status = next((s for s in statuses if s != "ok"), "ok")
                else:
                    value = (await loc.nth(0).inner_text()).strip() if count >= 1 else None
                    data[name] = value
                    status = check_dq(value, dq, in_scope=True)

                field_status[name] = status
                if status != "ok":
                    flags[name] = [status]

            await context.close()
        finally:
            await browser.close()

    return {"data": data, "field_status": field_status, "flags": flags}
