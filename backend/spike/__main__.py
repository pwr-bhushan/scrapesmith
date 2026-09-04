"""Bench CLI — measure heal success over the drift fixture corpus.

    .venv/bin/python -m spike --fixtures fixtures/drift --provider ollama --out artifacts

Wiring only: load_case → run_bench → compute_metrics → render_table / write_artifacts.

ponytail: argparse, no click. One command with four flags does not need a framework.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

from spike.bench import compute_metrics, load_case, run_bench
from spike.report import render_table, write_artifacts


def make_provider(name: str):
    """Resolve a provider name to an instance. Imported lazily so one provider's deps
    are not required to bench the other."""
    if name == "ollama":
        from spike.heal.ollama_provider import OllamaProvider

        return OllamaProvider()
    if name == "cloud":
        from spike.heal.cloud_provider import CloudProvider

        return CloudProvider()
    raise ValueError(f"Unknown provider {name!r}; expected 'ollama' or 'cloud'")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="spike", description=__doc__.splitlines()[0])
    parser.add_argument(
        "--fixtures", default="fixtures/drift",
        help="Directory of case directories (default: fixtures/drift)",
    )
    parser.add_argument(
        "--provider", default="ollama", choices=("ollama", "cloud"),
        help="Heal provider to benchmark (default: ollama)",
    )
    parser.add_argument(
        "--out", default=None,
        help="Write phase0_report.{json,md} here. Omit to only print the table.",
    )
    parser.add_argument(
        "--case", action="append", default=None,
        help="Run only this case directory name. Repeatable. Default: all.",
    )
    args = parser.parse_args(argv)

    root = pathlib.Path(args.fixtures)
    if not root.is_dir():
        parser.error(f"--fixtures {root} is not a directory")

    case_dirs = sorted(d for d in root.iterdir() if (d / "case.json").is_file())
    if args.case:
        wanted = set(args.case)
        case_dirs = [d for d in case_dirs if d.name in wanted]
        missing = wanted - {d.name for d in case_dirs}
        if missing:
            parser.error(f"no such case(s) under {root}: {', '.join(sorted(missing))}")
    if not case_dirs:
        parser.error(f"no cases with a case.json under {root}")

    cases = [load_case(str(d)) for d in case_dirs]
    n_fields = sum(len(c.fields) for c in cases)
    print(f"{len(cases)} cases, {n_fields} fields, provider={args.provider}", file=sys.stderr)

    results = run_bench(cases, [make_provider(args.provider)])
    metrics = compute_metrics(results)
    print(render_table(results, metrics))

    if args.out:
        write_artifacts(results, metrics, output_dir=args.out)
        print(f"\nwrote {args.out}/phase0_report.json and .md", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
