from __future__ import annotations

import argparse
from collections.abc import Sequence

from roster_generator.config import DEFAULT_CONFIG_PATH, load_config
from roster_generator.pipeline import generate_roster


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="roster-generator",
        description="Generate a normalized player-only roster package.",
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Path to YAML config.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    generate = subparsers.add_parser("generate", help="Generate a roster CSV package.")
    generate.add_argument(
        "--reference-package",
        default=None,
        help="Override the published reference-package directory.",
    )
    generate.add_argument("--output", default=None, help="Override the roster-package directory.")
    generate.add_argument("--formula", default=None, help="Override the formula JSON document.")
    generate.add_argument("--seed", type=int, default=None, help="Override the generation seed.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    config, _ = load_config(args.config)
    if args.command == "generate":
        output = generate_roster(
            config,
            reference_package=args.reference_package,
            output=args.output,
            formula_path=args.formula,
            seed=args.seed,
        )
        print(f"Published normalized roster package to {output}.")
        return 0
    raise AssertionError(f"Unhandled command: {args.command}")
