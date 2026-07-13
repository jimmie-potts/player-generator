from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from reference_data_app.adapters import SUPPORTED_SOURCE_TYPES, AdapterValidationError
from reference_data_app.config import DEFAULT_CONFIG_PATH, load_config, resolve_path
from reference_data_app.pipeline import build_reference_data, download_reference_data
from reference_data_app.publication import publish_reference_package
from reference_data_app.registration import RegistrationError, register_sources


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
    register = subparsers.add_parser("register", help="Register local Parquet source files.")
    register.add_argument("paths", nargs="+", type=Path, help="Local Parquet path(s) to register.")
    register.add_argument(
        "--source-type",
        required=True,
        choices=SUPPORTED_SOURCE_TYPES,
        help="Source adapter type for every supplied path.",
    )
    register.add_argument(
        "--adapter-version",
        type=int,
        default=1,
        help="Source adapter schema version (default: 1).",
    )
    register.add_argument(
        "--source-id",
        help="Explicit source ID; valid only when registering exactly one path.",
    )
    register.add_argument("--upstream-version", help="Known upstream version or snapshot label.")
    register.add_argument("--license-status", help="Known license status for the local source.")
    publish = subparsers.add_parser("publish", help="Publish normalized reference CSVs.")
    publish.add_argument("--output", type=Path, help="Override the configured package directory.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
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
    if args.command == "register":
        if args.source_id is not None and len(args.paths) != 1:
            parser.error("--source-id can only be used with exactly one path")
        try:
            sources = register_sources(
                args.paths,
                registry_path=resolve_path(config, "source_registry"),
                source_type=args.source_type,
                adapter_version=args.adapter_version,
                source_id=args.source_id,
                upstream_version=args.upstream_version,
                license_status=args.license_status,
            )
        except (AdapterValidationError, RegistrationError) as error:
            parser.error(str(error))
        print(f"Registered or verified {len(sources)} local reference source(s).")
        return 0
    if args.command == "publish":
        package_path = publish_reference_package(config, args.output)
        print(f"Published normalized reference package to {package_path}.")
        return 0
    raise AssertionError(f"Unhandled command: {args.command}")
