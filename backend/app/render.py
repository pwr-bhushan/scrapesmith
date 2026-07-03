"""Minimal Playwright pool. Phase 0.5: prove we can render a file headless in an isolated context.

Real pool sizing / lifecycle (design §7) lands in Phase 1. This is one browser, one ephemeral
context per call — enough to smoke-test that Chromium renders our fixtures.
"""
from __future__ import annotations

from pathlib import Path

from lxml import html as lxml_html
from playwright.async_api import async_playwright

# Strict CSP for the streamed snapshot: no external anything, only our inline overlay + styles.
_CSP = (
    "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; "
    "img-src data:; font-src data:"
)

# Hover-outline overlay (Phase 1). Click-to-select is Phase 2.
_OVERLAY_JS = """
(function () {
  var last = null;
  document.addEventListener('mouseover', function (e) {
    if (last) { last.style.outline = last.__ss_prev || ''; }
    last = e.target;
    last.__ss_prev = last.style.outline;
    last.style.outline = '2px solid #4f46e5';
  }, true);
  document.addEventListener('mouseout', function () {
    if (last) { last.style.outline = last.__ss_prev || ''; last = null; }
  }, true);
})();
"""


async def _block_egress(route):
    """Abort any non-file request so untrusted HTML can't reach the network (§14 SSRF/egress)."""
    url = route.request.url
    if url.startswith("file:") or url.startswith("data:"):
        await route.continue_()
    else:
        await route.abort()


def _sanitize_snapshot(content: str) -> str:
    """Strip all page scripts, inject a strict CSP + our overlay. Returns standalone HTML."""
    tree = lxml_html.fromstring(content)
    for bad in tree.xpath("//script | //noscript"):
        bad.getparent().remove(bad)

    head = tree.find("head")
    if head is None:
        head = lxml_html.Element("head")
        tree.insert(0, head)
    meta = lxml_html.Element("meta")
    meta.set("http-equiv", "Content-Security-Policy")
    meta.set("content", _CSP)
    head.insert(0, meta)

    body = tree.find("body")
    if body is None:
        body = tree
    overlay = lxml_html.Element("script")
    overlay.set("data-scrapesmith-overlay", "1")
    overlay.text = _OVERLAY_JS
    body.append(overlay)

    return lxml_html.tostring(tree, encoding="unicode", doctype="<!DOCTYPE html>")


async def render_snapshot(path: str, render_js: bool = True) -> str:
    """Render a local HTML file headless in an isolated, egress-blocked context; return a sanitized,
    overlay-injected, CSP-locked snapshot safe to stream into a sandboxed iframe."""
    url = Path(path).resolve().as_uri()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context(java_script_enabled=render_js)
            page = await context.new_page()
            await page.route("**/*", _block_egress)
            await page.goto(url)
            content = await page.content()
            await context.close()
            return _sanitize_snapshot(content)
        finally:
            await browser.close()


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
