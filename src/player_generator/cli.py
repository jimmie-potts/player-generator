from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from player_generator.config import load_config
from player_generator.pipeline import (
    build_reference_data,
    compare_generated_roster,
    download_reference_data,
    generate_roster,
    raw_reference_files_exist,
    reference_snapshot_exists,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="player-generator",
        description="Build named reference profiles and generate a fictional basketball league.",
    )
    parser.add_argument("--config", default="config/default.yaml", help="Path to YAML config.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    download = subparsers.add_parser("download-reference", help="Download local source data.")
    download.add_argument("--force", action="store_true", help="Replace existing raw files.")

    subparsers.add_parser("build-reference", help="Build non-anonymized reference profiles.")

    generate = subparsers.add_parser("generate", help="Generate fictional teams and players.")
    generate.add_argument("--seed", type=int, default=None, help="Override the generation seed.")

    subparsers.add_parser("compare", help="Compare generated and named reference distributions.")

    all_command = subparsers.add_parser("all", help="Run all locally available pipeline stages.")
    all_command.add_argument("--seed", type=int, default=None, help="Override the generation seed.")
    all_command.add_argument(
        "--refresh-reference",
        action="store_true",
        help="Download and rebuild the local reference snapshot before generation.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    config, _ = load_config(Path(args.config))

    if args.command == "download-reference":
        paths = download_reference_data(config, force=args.force)
        print(f"Downloaded or verified {len(paths)} reference files.")
        return 0

    if args.command == "build-reference":
        seasons, snapshot = build_reference_data(config)
        print(f"Wrote {seasons}")
        print(f"Wrote {snapshot}")
        return 0

    if args.command == "generate":
        roster, players = generate_roster(config, seed=args.seed)
        print(f"Wrote {roster}")
        print(f"Wrote {players}")
        return 0

    if args.command == "compare":
        report, table = compare_generated_roster(config)
        print(f"Wrote {report}")
        print(f"Wrote {table}")
        return 0

    if args.command == "all":
        if args.refresh_reference:
            download_reference_data(config, force=False)
            build_reference_data(config)
        elif raw_reference_files_exist(config):
            build_reference_data(config)
        elif not reference_snapshot_exists(config):
            download_reference_data(config, force=False)
            build_reference_data(config)
        roster, players = generate_roster(config, seed=args.seed)
        report, table = compare_generated_roster(config)
        print(f"Wrote {roster}")
        print(f"Wrote {players}")
        print(f"Wrote {report}")
        print(f"Wrote {table}")
        return 0

    raise AssertionError(f"Unhandled command: {args.command}")
