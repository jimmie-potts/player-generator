from __future__ import annotations

import argparse
from collections.abc import Sequence

import uvicorn

from formula_preview_api.app import create_app
from formula_preview_api.config import load_settings


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="formula-preview-api",
        description="Serve the versioned, read-only player formula preview API.",
    )
    parser.add_argument("--config", help="Path to the formula preview YAML configuration.")
    parser.add_argument(
        "--reference-package",
        help="Override the configured published reference package directory.",
    )
    parser.add_argument(
        "--season",
        type=int,
        help="Override the configured reference season cohort.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    settings = load_settings(args.config).with_overrides(
        reference_package=args.reference_package,
        season=args.season,
    )
    app = create_app(settings)
    uvicorn.run(app, host=args.host, port=args.port)
