"""Minimal Playwright pool. Phase 0.5: prove we can render a file headless in an isolated context.

Real pool sizing / lifecycle (design §7) lands in Phase 1. This is one browser, one ephemeral
context per call — enough to smoke-test that Chromium renders our fixtures.
"""
from __future__ import annotations

from pathlib import Path

from playwright.async_api import async_playwright


async def render_file(path: str) -> dict:
    """Render a local HTML file headless in an isolated context; return basic proof-of-render."""
    url = Path(path).resolve().as_uri()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto(url)
            title = await page.title()
            text = await page.inner_text("body")
            await context.close()
            return {"title": title, "text_len": len(text)}
        finally:
            await browser.close()
