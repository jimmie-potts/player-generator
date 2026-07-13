from __future__ import annotations

import argparse
from collections.abc import Sequence

from roster_generator.config import DEFAULT_CONFIG_PATH, load_config
from roster_generator.pipeline import compare_roster, generate_roster


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="roster-generator",
        description="Generate and compare basketball roster data.",
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Path to YAML config.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    generate = subparsers.add_parser("generate", help="Generate roster data.")
    generate.add_argument("--seed", type=int, default=None, help="Override the generation seed.")
    subparsers.add_parser("compare", help="Compare roster and reference distributions.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    config, _ = load_config(args.config)
    if args.command == "generate":
        roster, players = generate_roster(config, seed=args.seed)
        print(f"Wrote {roster}")
        print(f"Wrote {players}")
        return 0
    if args.command == "compare":
        report, table = compare_roster(config)
        print(f"Wrote {report}")
        print(f"Wrote {table}")
        return 0
    raise AssertionError(f"Unhandled command: {args.command}")
