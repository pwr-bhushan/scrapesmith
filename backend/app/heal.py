"""Heal orchestration (design §10): trigger → cluster → propose → post-check.

Anchor-correctness is enforced HERE (post_check step 5), independent of the model prompt: a
proposal that passes DQ but diverges from the field anchor is marked `suspect`, never auto-applied.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright

from app.dq import check_dq, normalize
from app.render import _block_egress

FIELD_DRIFT_THRESHOLD = 0.30
_NTH_CHILD = re.compile(r"nth-child")
_INDEX = re.compile(r":nth-of-type\(\d+\)|\[\d+\]")


def failing_fields(field_rates: dict, threshold: float = FIELD_DRIFT_THRESHOLD) -> list:
    """Fields whose failure_rate ≥ threshold (§9 per-field heal trigger)."""
    return [name for name, r in field_rates.items() if r["failure_rate"] >= threshold]


def cluster_failures(results: list, failing: list) -> list:
    """Cluster failing files by dom_skeleton_hash; rep = centroid (largest bucket's first)."""
    # a file is "failing" if any failing field is non-ok on it
    def is_failing(r):
        return any(r["field_status"].get(f, "ok") not in ("ok", "out_of_scope") for f in failing)

    buckets: dict = {}
    for r in results:
        if is_failing(r):
            buckets.setdefault(r.get("dom_skeleton_hash", ""), []).append(r)

    clusters = []
    for h, files in sorted(buckets.items(), key=lambda kv: -len(kv[1])):
        clusters.append({"hash": h, "representative": files[0], "files": files, "size": len(files)})
    return clusters


def is_too_positional(selector: str) -> bool:
    """Reject selectors relying on deep nth-child or >1 numeric index (§10 step 4)."""
    if _NTH_CHILD.search(selector):
        return True
    return len(_INDEX.findall(selector)) > 1


def select_provider():
    """Cloud if key, Ollama if host, else None (heal can't run — surface drift only)."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        from spike.heal.cloud_provider import CloudProvider

        return CloudProvider()
    if os.environ.get("OLLAMA_HOST"):
        from spike.heal.ollama_provider import OllamaProvider

        return OllamaProvider()
    return None


async def _resolve(page, selector: str):
    try:
        loc = page.locator(selector)
        count = await loc.count()
        value = (await loc.nth(0).inner_text()).strip() if count else None
        return count, value
    except Exception:
        return 0, None


async def post_check(
    proposals: dict, rep_path: str, cluster_paths: list, fields_by_name: dict, render_js: bool
) -> dict:
    """Run §10 steps 1–6 per field. Returns {field: {selector, status, value, anchor_ok}}."""
    out: dict = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context(java_script_enabled=render_js)
            page = await context.new_page()
            await page.route("**/*", _block_egress)
            await page.goto(Path(rep_path).resolve().as_uri())

            for name, selector in proposals.items():
                field = fields_by_name.get(name, {})
                dq = field.get("dq") or {}
                anchor = (field.get("anchor") or {}).get("value")
                kind = "number" if dq.get("parses_as") == "number" else "text"

                # step 1: valid prefix
                if not (selector.startswith("css=") or selector.startswith("xpath=")):
                    out[name] = _bad(selector, "still_broken")
                    continue
                # step 4: not too positional
                if is_too_positional(selector):
                    out[name] = _bad(selector, "still_broken")
                    continue
                # step 2: resolves
                count, value = await _resolve(page, selector)
                if not count:
                    out[name] = _bad(selector, "still_broken")
                    continue
                # step 3: DQ
                if check_dq(value, dq) != "ok":
                    out[name] = _bad(selector, "still_broken", value)
                    continue
                # step 5: anchor check
                if anchor is None:
                    anchor_ok = None
                else:
                    anchor_ok = normalize(value, kind) == normalize(anchor, kind)
                # step 6: validate on up to 2 more cluster files
                extra_ok = await _validate_others(
                    browser, cluster_paths, selector, dq, render_js
                )
                status = "healed" if (anchor_ok is not False and extra_ok) else "suspect"
                out[name] = {
                    "selector": selector,
                    "status": status,
                    "value": value,
                    "anchor_ok": anchor_ok,
                }
            await context.close()
        finally:
            await browser.close()
    return out


def _bad(selector: str, status: str, value: Optional[str] = None) -> dict:
    return {"selector": selector, "status": status, "value": value, "anchor_ok": None}


async def _validate_others(browser, cluster_paths, selector, dq, render_js) -> bool:
    """Both of the next ≤2 cluster files must resolve + pass DQ (§10 step 6)."""
    checked = 0
    for path in cluster_paths[:2]:
        ctx = await browser.new_context(java_script_enabled=render_js)
        page = await ctx.new_page()
        await page.route("**/*", _block_egress)
        await page.goto(Path(path).resolve().as_uri())
        count, value = await _resolve(page, selector)
        await ctx.close()
        if not count or check_dq(value, dq) != "ok":
            return False
        checked += 1
    return checked > 0 or len(cluster_paths) == 0
