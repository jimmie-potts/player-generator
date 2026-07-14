from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from player_attribute_engine import FormulaDocument
from player_data_contracts import (
    SUPPORTED_REFERENCE_CONTRACT_VERSIONS,
    ReferencePackageIntegrityError,
    load_reference_package_tables,
    load_roster_contract,
)

MANIFEST_FILENAME = "manifest.json"


class ReferencePackageError(ValueError):
    """Raised when a published reference package is unsafe to consume."""


@dataclass(frozen=True)
class LoadedReferencePackage:
    """A validated reference package and its internal joined player-season rows."""

    path: Path
    manifest: Mapping[str, Any]
    content_hash: str
    frame: pd.DataFrame
    forbidden_names: frozenset[str]
    forbidden_player_ids: frozenset[str]
    forbidden_team_ids: frozenset[str]

    @property
    def forbidden_reference_names(self) -> frozenset[str]:
        """Expose the provenance meaning of ``forbidden_names`` explicitly."""
        return self.forbidden_names


def _manifest_integer(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ReferencePackageError(f"Reference manifest field {field} must be an integer.")
    return value


def _read_manifest(path: Path) -> dict[str, Any]:
    manifest_path = path / MANIFEST_FILENAME
    if not manifest_path.is_file():
        raise ReferencePackageError(
            f"Reference package is missing required file {MANIFEST_FILENAME}: {manifest_path}"
        )
    try:
        with manifest_path.open("r", encoding="utf-8") as handle:
            manifest = json.load(handle)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ReferencePackageError(
            f"Unable to parse reference package file {MANIFEST_FILENAME}: {error}"
        ) from error
    if not isinstance(manifest, dict):
        raise ReferencePackageError(
            f"Reference package file {MANIFEST_FILENAME} must be an object."
        )
    return manifest


def _package_version(manifest: Mapping[str, Any]) -> int:
    package_version = _manifest_integer(manifest.get("packageVersion"), "packageVersion")
    if package_version not in SUPPORTED_REFERENCE_CONTRACT_VERSIONS:
        supported = ", ".join(str(version) for version in SUPPORTED_REFERENCE_CONTRACT_VERSIONS)
        raise ReferencePackageError(
            "Reference manifest uses unsupported packageVersion "
            f"{package_version}; supported versions are {supported}."
        )
    return package_version


def _formula_contract_version(formula: object) -> int:
    if isinstance(formula, Mapping):
        value = formula.get("reference_contract_version", formula.get("referenceContractVersion"))
    else:
        value = getattr(formula, "reference_contract_version", None)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ReferencePackageError(
            "Formula is missing a valid reference_contract_version compatibility declaration."
        )
    return value


def _formula_output_fields(formula: object) -> tuple[str, ...]:
    if isinstance(formula, Mapping):
        value = formula.get("output_fields", formula.get("outputFields"))
    else:
        value = getattr(formula, "output_fields", None)
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise ReferencePackageError(
            "Formula is missing a valid ordered output_fields compatibility declaration."
        )
    return tuple(str(field) for field in value)


def _formula_input_fields(formula: object) -> frozenset[str]:
    if isinstance(formula, Mapping):
        metrics = formula.get("metrics")
    else:
        metrics = getattr(formula, "metrics", None)
    if not isinstance(metrics, Mapping):
        raise ReferencePackageError(
            "Formula is missing a valid metrics compatibility declaration."
        )

    fields: set[str] = set()
    for name, metric in metrics.items():
        if isinstance(metric, Mapping):
            kind = metric.get("kind")
            field = metric.get("field")
        else:
            kind = getattr(metric, "kind", None)
            field = getattr(metric, "field", None)
        if kind != "input":
            continue
        if not isinstance(field, str) or not field:
            raise ReferencePackageError(
                f"Formula input metric {name!r} is missing a valid field declaration."
            )
        fields.add(field)
    return frozenset(fields)


def _validate_formula_compatibility(formula: object, package_version: int) -> None:
    formula_version = _formula_contract_version(formula)
    if (
        formula_version not in SUPPORTED_REFERENCE_CONTRACT_VERSIONS
        or formula_version > package_version
    ):
        raise ReferencePackageError(
            "Formula reference contract version is incompatible with the reference package: "
            f"formula requires {formula_version}, package provides {package_version}."
        )

    roster_contract = load_roster_contract()
    expected_formula_outputs = tuple(
        str(column["name"])
        for column in roster_contract["files"]["player_attributes.csv"]["columns"]
    )
    actual_formula_outputs = _formula_output_fields(formula)
    if actual_formula_outputs != expected_formula_outputs:
        raise ReferencePackageError(
            "Formula output_fields are incompatible with roster contract version 1: "
            f"expected {expected_formula_outputs!r}, found {actual_formula_outputs!r}."
        )
    evaluation_inputs = {
        str(column["name"])
        for filename in ("player_stats.csv", "player_advanced_stats.csv")
        for column in roster_contract["files"][filename]["columns"]
    }
    missing_formula_inputs = sorted(_formula_input_fields(formula) - evaluation_inputs)
    if missing_formula_inputs:
        raise ReferencePackageError(
            "Formula input fields are unavailable in the roster contract version 1 "
            "attribute-evaluation frame: "
            f"{', '.join(missing_formula_inputs)}."
        )


def _pandas_dtypes(file_contract: Mapping[str, Any]) -> dict[str, str]:
    dtypes: dict[str, str] = {}
    for column in file_contract["columns"]:
        field_type = column["type"]
        name = column["name"]
        if field_type == "integer":
            dtypes[name] = "Int64"
        elif field_type == "number":
            dtypes[name] = "Float64"
        else:
            dtypes[name] = "string"
    return dtypes


def _read_typed_tables(
    rows_by_file: Mapping[str, Sequence[Mapping[str, object]]],
    contract: Mapping[str, Any],
) -> dict[str, pd.DataFrame]:
    tables: dict[str, pd.DataFrame] = {}
    for filename, file_contract in contract["files"].items():
        columns = [str(column["name"]) for column in file_contract["columns"]]
        frame = pd.DataFrame.from_records(rows_by_file[filename], columns=columns)
        tables[filename] = frame.astype(_pandas_dtypes(file_contract))
    return tables


def _joined_frame(tables: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    keys = ["playerSeasonId", "playerId", "season"]
    seasons = tables["player_seasons.csv"]
    joined = seasons.merge(
        tables["players.csv"], on="playerId", how="left", validate="many_to_one", sort=False
    )
    joined = joined.merge(
        tables["player_stats.csv"], on=keys, how="left", validate="one_to_one", sort=False
    )
    joined = joined.merge(
        tables["player_advanced_stats.csv"],
        on=keys,
        how="left",
        validate="one_to_one",
        sort=False,
    )
    return joined.sort_values(["season", "playerSeasonId"], kind="stable").reset_index(drop=True)


def _forbidden_names(players: pd.DataFrame) -> frozenset[str]:
    values: set[str] = set()
    for row in players[["displayName", "firstName", "lastName"]].itertuples(index=False):
        candidates = [row.displayName]
        parts = [part for part in (row.firstName, row.lastName) if not pd.isna(part)]
        if parts:
            candidates.append(" ".join(str(part) for part in parts))
        for candidate in candidates:
            if not pd.isna(candidate) and str(candidate).strip():
                values.add(str(candidate).strip().casefold())
    return frozenset(values)


def _non_null_strings(values: pd.Series, *, casefold: bool = False) -> frozenset[str]:
    strings = (str(value) for value in values if not pd.isna(value) and str(value))
    return frozenset(value.casefold() if casefold else value for value in strings)


def load_reference_package(
    path: str | Path,
    formula: FormulaDocument | Mapping[str, object] | object,
) -> LoadedReferencePackage:
    """Load, validate, and join a supported published reference package."""
    directory = Path(path).expanduser().resolve()
    if not directory.is_dir():
        raise ReferencePackageError(f"Reference package directory does not exist: {directory}")

    manifest = _read_manifest(directory)
    package_version = _package_version(manifest)
    _validate_formula_compatibility(formula, package_version)

    try:
        loaded = load_reference_package_tables(
            directory,
            allowed_versions=SUPPORTED_REFERENCE_CONTRACT_VERSIONS,
        )
    except ReferencePackageIntegrityError as error:
        raise ReferencePackageError(str(error)) from error
    if loaded.package_version != package_version:
        raise ReferencePackageError("Reference manifest packageVersion changed while validating.")

    tables = _read_typed_tables(loaded.tables, loaded.contract)
    players = tables["players.csv"]
    seasons = tables["player_seasons.csv"]
    source_ids = tables["player_source_ids.csv"]
    forbidden_player_ids = set(_non_null_strings(players["playerId"], casefold=True))
    forbidden_player_ids.update(
        _non_null_strings(source_ids["sourcePlayerId"], casefold=True)
    )
    return LoadedReferencePackage(
        path=loaded.path,
        manifest=loaded.manifest,
        content_hash=loaded.content_hash,
        frame=_joined_frame(tables),
        forbidden_names=_forbidden_names(players),
        forbidden_player_ids=frozenset(forbidden_player_ids),
        forbidden_team_ids=_non_null_strings(seasons["teamId"], casefold=True),
    )


__all__ = [
    "LoadedReferencePackage",
    "ReferencePackageError",
    "load_reference_package",
]
