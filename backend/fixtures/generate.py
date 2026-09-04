"""Generate the drift eval corpus: base pages × labelled drift transforms.

Run from `backend/`:  .venv/bin/python fixtures/generate.py

Output is **committed**, not generated at bench time. Two reasons: a reviewer can read the cases,
and the baseline number cannot quietly move between runs because a transform changed.

A field is only written into a case if it actually drifted — the old selector matched `before.html`
and does not match `after.html`. `attr_strip` does not break a class-based selector, so pretending
every field drifts under every transform would pad the corpus with cases where the correct answer
is "the old selector still works", and inflate the heal rate.

ponytail: soup.select for the drift check rather than Playwright. It is a "does this still match"
question over simple selectors, and 120 Chromium launches to answer it at generation time is not a
trade. The bench itself still resolves through Playwright, which stays the source of truth.
"""
from __future__ import annotations

import json
import pathlib
import sys

from bs4 import BeautifulSoup

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from spike.mutate import DRIFT_TYPES, apply_drift  # noqa: E402

HERE = pathlib.Path(__file__).parent
BASE_DIR = HERE / "base"
OUT_DIR = HERE / "drift"


def bare(selector: str) -> str:
    """Strip the `css=` prefix the bench uses; soup.select wants the raw selector."""
    return selector.removeprefix("css=")


def build_case(base_name: str, drift_type: str) -> dict | None:
    """Write one fixture directory. Returns a summary dict, or None if nothing drifted."""
    before = (BASE_DIR / f"{base_name}.html").read_text(encoding="utf-8")
    meta = json.loads((BASE_DIR / f"{base_name}.json").read_text(encoding="utf-8"))

    selectors = [bare(f["old_selector"]) for f in meta["fields"]]
    after = apply_drift(before, drift_type, selectors)

    soup_before = BeautifulSoup(before, "html.parser")
    soup_after = BeautifulSoup(after, "html.parser")

    drifted = []
    for field in meta["fields"]:
        sel = bare(field["old_selector"])
        matched = soup_before.select(sel)
        if not matched:
            raise ValueError(
                f"{base_name}: {field['name']} selector {sel!r} matches nothing in the base page"
            )
        if matched[0].get_text(strip=True) != field["anchor"]:
            raise ValueError(
                f"{base_name}: {field['name']} anchor {field['anchor']!r} != "
                f"{matched[0].get_text(strip=True)!r} in the base page"
            )
        if soup_after.select(sel):
            continue  # this transform did not break this field — nothing to heal
        if field["anchor"] not in soup_after.get_text():
            raise ValueError(
                f"{base_name}/{drift_type}: transform destroyed {field['name']}'s value"
            )
        drifted.append(field)

    if not drifted:
        return None

    case_dir = OUT_DIR / f"{base_name}__{drift_type}"
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "before.html").write_text(before, encoding="utf-8")
    (case_dir / "after.html").write_text(after, encoding="utf-8")
    (case_dir / "case.json").write_text(
        json.dumps(
            {
                "host": meta["host"],
                "page_type": meta["page_type"],
                "drift_type": drift_type,
                "fields": drifted,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return {"case": case_dir.name, "fields": [f["name"] for f in drifted]}


def main() -> None:
    bases = sorted(p.stem for p in BASE_DIR.glob("*.html"))
    written, skipped, n_fields = [], [], 0
    for base_name in bases:
        for drift_type in DRIFT_TYPES:
            summary = build_case(base_name, drift_type)
            if summary is None:
                skipped.append(f"{base_name}__{drift_type}")
                continue
            written.append(summary)
            n_fields += len(summary["fields"])

    for s in written:
        print(f"  {s['case']:<32} {', '.join(s['fields'])}")
    if skipped:
        print(f"\nskipped (no field drifted): {', '.join(skipped)}")
    print(f"\n{len(written)} cases, {n_fields} drifted fields, from {len(bases)} base pages")


if __name__ == "__main__":
    main()
