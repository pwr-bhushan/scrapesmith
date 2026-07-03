"""Resolve candidate selectors against the raw rendered file (design §8.1 round-trip parity).

Renders the file once in an isolated, egress-blocked context and counts each candidate via
Playwright locator() — the same engine the extractor uses, so a green check means it truly resolves.
"""
from __future__ import annotations

from pathlib import Path

from playwright.async_api import async_playwright

from app.render import _block_egress

_MAX_SAMPLE = 10


async def resolve_many(raw_path: str, selectors: list, render_js: bool) -> list:
    """Return [{selector, count, values[]}] for each candidate, one render."""
    url = Path(raw_path).resolve().as_uri()
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context(java_script_enabled=render_js)
            page = await context.new_page()
            await page.route("**/*", _block_egress)
            await page.goto(url)
            for sel in selectors:
                try:
                    loc = page.locator(sel)
                    count = await loc.count()
                    values = []
                    for i in range(min(count, _MAX_SAMPLE)):
                        values.append((await loc.nth(i).inner_text()).strip())
                except Exception:
                    count, values = 0, []
                results.append({"selector": sel, "count": count, "values": values})
            await context.close()
        finally:
            await browser.close()
    return results


async def resolve_on_file(raw_path: str, selector: str, render_js: bool) -> dict:
    return (await resolve_many(raw_path, [selector], render_js))[0]
