from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from player_attribute_engine import load_formula_snapshot

from roster_generator.config import resolve_optional_path, resolve_path
from roster_generator.generator import generate_roster_tables
from roster_generator.publication import publish_roster_package
from roster_generator.reference_package import load_reference_package


def _override_path(value: str | Path | None) -> Path | None:
    return None if value is None else Path(value).expanduser().resolve()


def generate_roster(
    config: Mapping[str, Any],
    *,
    reference_package: str | Path | None = None,
    output: str | Path | None = None,
    formula_path: str | Path | None = None,
    seed: int | None = None,
) -> Path:
    configured_formula = resolve_optional_path(config, "formula_path")
    active_formula_path = _override_path(formula_path) or configured_formula
    formula, formula_hash = load_formula_snapshot(active_formula_path)
    reference_path = _override_path(reference_package) or resolve_path(
        dict(config), "reference_package_dir"
    )
    destination = _override_path(output) or resolve_path(dict(config), "roster_package_dir")

    loaded_reference = load_reference_package(reference_path, formula)
    generated = generate_roster_tables(loaded_reference, formula, config, seed=seed)
    return publish_roster_package(
        generated,
        loaded_reference,
        destination,
        formula_version=formula.formula_version,
        formula_hash=formula_hash,
    )
