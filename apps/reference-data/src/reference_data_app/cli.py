from __future__ import annotations

import argparse
from collections.abc import Sequence

from reference_data_app.config import DEFAULT_CONFIG_PATH, load_config
from reference_data_app.pipeline import build_reference_data, download_reference_data


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reference-data",
        description="Build local named basketball reference data.",
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Path to YAML config.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    download = subparsers.add_parser("download", help="Download the current pinned source data.")
    download.add_argument("--force", action="store_true", help="Replace existing raw files.")
    subparsers.add_parser("build", help="Build the current processed reference profiles.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    config, _ = load_config(args.config)
    if args.command == "download":
        paths = download_reference_data(config, force=args.force)
        print(f"Downloaded or verified {len(paths)} reference files.")
        return 0
    if args.command == "build":
        seasons, snapshot = build_reference_data(config)
        print(f"Wrote {seasons}")
        print(f"Wrote {snapshot}")
        return 0
    raise AssertionError(f"Unhandled command: {args.command}")
