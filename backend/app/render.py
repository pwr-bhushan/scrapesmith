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

# Overlay: hover outline + click-to-select. On click it builds an element descriptor + detects a
# list container (§8.2) and postMessages to the parent app, which calls /pick/validate.
_OVERLAY_JS = """
(function () {
  var LANDMARKS = ['main', 'nav', 'header', 'footer', 'article', 'section'];
  var STABLE = /^[a-zA-Z]{3,}(?:-[a-zA-Z]+)*$/;

  function stableClasses(el) {
    return Array.prototype.filter.call(el.classList || [], function (c) { return STABLE.test(c); });
  }
  function landmarkOf(el) {
    for (var n = el; n && n.tagName; n = n.parentElement) {
      var t = n.tagName.toLowerCase();
      if (LANDMARKS.indexOf(t) !== -1) return t;
    }
    return null;
  }
  function nthOfType(el) {
    var i = 1, tag = el.tagName;
    for (var s = el.previousElementSibling; s; s = s.previousElementSibling) {
      if (s.tagName === tag) i++;
    }
    return i;
  }
  function dataAttrs(el) {
    var d = {};
    Array.prototype.forEach.call(el.attributes || [], function (a) {
      if (a.name.indexOf('data-') === 0) d[a.name] = a.value;
    });
    return d;
  }
  function descriptor(el) {
    return {
      tag: el.tagName.toLowerCase(),
      id: el.id || '',
      classes: stableClasses(el),
      data: dataAttrs(el),
      itemprop: el.getAttribute('itemprop') || '',
      role: el.getAttribute('role') || '',
      landmark: landmarkOf(el),
      nth_of_type: nthOfType(el)
    };
  }
  // §8.2: nearest ancestor container whose children (>=3) share tag + >=60% stable-class overlap
  function listParent(el) {
    for (var n = el.parentElement; n && n.tagName; n = n.parentElement) {
      var kids = Array.prototype.filter.call(n.children, function (c) { return c.tagName; });
      if (kids.length < 3) continue;
      var byTag = {};
      kids.forEach(function (k) { byTag[k.tagName] = (byTag[k.tagName] || 0) + 1; });
      var domTag = Object.keys(byTag).sort(function (a, b) { return byTag[b] - byTag[a]; })[0];
      var group = kids.filter(function (k) { return k.tagName === domTag; });
      if (group.length < 3) continue;
      var base = stableClasses(group[0]);
      var ok = group.filter(function (k) {
        var cs = stableClasses(k);
        if (!base.length && !cs.length) return true;
        var shared = base.filter(function (c) { return cs.indexOf(c) !== -1; }).length;
        var denom = Math.max(base.length, cs.length) || 1;
        return shared / denom >= 0.6;
      });
      if (ok.length >= 3) {
        var lm = landmarkOf(n);
        var cls = stableClasses(n)[0];
        var sel = (lm ? lm + ' ' : '') + n.tagName.toLowerCase() + (cls ? '.' + cls : '');
        return { selector: sel, count: group.length };
      }
    }
    return null;
  }

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
  document.addEventListener('click', function (e) {
    e.preventDefault();
    e.stopPropagation();
    var el = e.target;
    window.parent.postMessage({
      type: 'scrapesmith-pick',
      descriptor: descriptor(el),
      text: (el.innerText || '').trim().slice(0, 120),
      listParent: listParent(el)
    }, '*');
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
