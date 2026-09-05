"""Bench CLI — measure heal success over the drift fixture corpus.

    .venv/bin/python -m spike --fixtures fixtures/drift --provider ollama --out artifacts

Wiring only: load_case → run_bench → compute_metrics → render_table / write_artifacts.

ponytail: argparse, no click. One command with four flags does not need a framework.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

from spike.bench import compare_metrics, compute_metrics, load_case, run_bench
from spike.memory import build_entries, load_store, save_store
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
        "--k",
        type=int,
        default=0,
        help="few-shot examples retrieved from heal memory (default: 0, the baseline arm)",
    )
    parser.add_argument(
        "--partition",
        choices=("loo", "lobo"),
        default="loo",
        help="loo = leave this case out of memory; lobo = leave its whole base page out "
             "(the honest transfer number). Only used when --k > 0.",
    )
    parser.add_argument(
        "--memory",
        default="artifacts/heal_memory.jsonl",
        help="heal memory store to retrieve from (default: artifacts/heal_memory.jsonl)",
    )
    parser.add_argument(
        "--save-memory",
        action="store_true",
        help="write this run's successful heals to --memory. Run once at --k 0 to seed the "
             "store; k>0 arms read it and must not overwrite it.",
    )
    parser.add_argument(
        "--case", action="append", default=None,
        help="Run only this case directory name. Repeatable. Default: all.",
    )
    parser.add_argument(
        "--baseline",
        default=None,
        help="Compare this run's metrics against a previous phase0_report.json and print the "
             "deltas plus a regression verdict.",
    )
    args = parser.parse_args(argv)

    # --save-memory writes the whole store, so a run that is not the full k=0 baseline would
    # replace it with a partial or few-shot-assisted one — and every later arm reads it.
    if args.save_memory and args.k > 0:
        parser.error("--save-memory requires --k 0: memory seeded from a few-shot run teaches "
                     "the model its own retrieved answers")
    if args.save_memory and args.case:
        parser.error("--save-memory requires the full corpus: --case would truncate the store "
                     "to the selected cases")

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
    memory = load_store(args.memory) if args.k > 0 else []
    if args.k > 0 and not memory:
        print(f"warning: --k {args.k} but {args.memory} is empty — this run is a k=0 arm",
              file=sys.stderr)

    print(
        f"{len(cases)} cases, {n_fields} fields, provider={args.provider}, "
        f"k={args.k}, partition={args.partition}, memory={len(memory)} entries",
        file=sys.stderr,
    )

    results = run_bench(
        cases,
        [make_provider(args.provider)],
        k=args.k,
        memory=memory,
        partition=args.partition,
    )
    metrics = compute_metrics(results)
    print(render_table(results, metrics))

    if args.out:
        write_artifacts(
            results,
            metrics,
            output_dir=args.out,
            arm={
                "provider": args.provider,
                "k": args.k,
                "partition": args.partition,
                "memory_entries": len(memory),
            },
        )
        print(f"\nwrote {args.out}/phase0_report.json and .md", file=sys.stderr)

    if args.baseline:
        base = json.loads(pathlib.Path(args.baseline).read_text(encoding="utf-8"))["metrics"]
        cmp = compare_metrics(base, metrics)
        print(
            f"\nvs {args.baseline}: healed {cmp['healed_rate_delta']:+.2%}  "
            f"resolve_but_wrong {cmp['resolve_but_wrong_rate_delta']:+.2%}  "
            f"regression={cmp['regression']}"
        )

    if args.save_memory:
        entries = build_entries(results, cases)
        save_store(args.memory, entries)
        print(f"wrote {len(entries)} memory entries to {args.memory}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
