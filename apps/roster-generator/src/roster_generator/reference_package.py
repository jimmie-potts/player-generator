from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

import pandas as pd
from player_attribute_engine import FormulaDocument
from player_data_contracts import (
    SUPPORTED_REFERENCE_CONTRACT_VERSIONS,
    ContractValidationError,
    load_reference_contract,
    load_roster_contract,
    validate_reference_package,
)
from player_data_contracts.io import sha256_file
from player_data_contracts.package import content_hash

AUDIT_FILENAME: Final = "audit.json"
MANIFEST_FILENAME: Final = "manifest.json"
MANIFEST_VERSION: Final = 1
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


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


def _manifest_mapping(value: object, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ReferencePackageError(f"Reference manifest field {field} must be an object.")
    return value


def _manifest_integer(value: object, field: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ReferencePackageError(f"Reference manifest field {field} must be an integer.")
    if minimum is not None and value < minimum:
        raise ReferencePackageError(f"Reference manifest field {field} must be at least {minimum}.")
    return value


def _manifest_hash(value: object, field: str) -> str:
    if not isinstance(value, str) or _SHA256_PATTERN.fullmatch(value) is None:
        raise ReferencePackageError(
            f"Reference manifest field {field} must be a lowercase SHA-256 hash."
        )
    return value


def _manifest_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReferencePackageError(f"Reference manifest field {field} must be a non-empty string.")
    return value


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


def _validate_manifest(
    directory: Path,
    manifest: Mapping[str, Any],
    csv_filenames: tuple[str, ...],
    formula: object,
    package_version: int,
) -> tuple[Mapping[str, Any], str]:
    manifest_version = _manifest_integer(manifest.get("manifestVersion"), "manifestVersion")
    if manifest_version != MANIFEST_VERSION:
        raise ReferencePackageError(
            "Reference manifest uses unsupported manifestVersion "
            f"{manifest_version}; supported version is {MANIFEST_VERSION}."
        )
    if manifest.get("packageType") != "reference":
        raise ReferencePackageError(
            "Reference manifest field packageType must equal 'reference'; "
            f"found {manifest.get('packageType')!r}."
        )
    if _package_version(manifest) != package_version:
        raise ReferencePackageError("Reference manifest packageVersion changed while validating.")

    expected_data_files = (*csv_filenames, AUDIT_FILENAME)
    file_entries = _manifest_mapping(manifest.get("files"), "files")
    missing_entries = sorted(set(expected_data_files) - set(file_entries))
    unexpected_entries = sorted(set(file_entries) - set(expected_data_files))
    if missing_entries or unexpected_entries:
        details: list[str] = []
        if missing_entries:
            details.append(f"missing {', '.join(missing_entries)}")
        if unexpected_entries:
            details.append(f"unexpected {', '.join(unexpected_entries)}")
        raise ReferencePackageError(
            "Reference manifest files must contain exactly the normalized CSV and audit files: "
            + "; ".join(details)
            + "."
        )

    actual_files = {entry.name for entry in directory.iterdir() if entry.is_file()}
    expected_files = {*expected_data_files, MANIFEST_FILENAME}
    missing_files = sorted(expected_files - actual_files)
    unexpected_files = sorted(actual_files - expected_files)
    if missing_files or unexpected_files:
        details = []
        if missing_files:
            details.append(f"missing {', '.join(missing_files)}")
        if unexpected_files:
            details.append(f"unexpected {', '.join(unexpected_files)}")
        raise ReferencePackageError(
            "Reference package directory must contain exactly the manifest-declared files: "
            + "; ".join(details)
            + "."
        )

    contract_versions = _manifest_mapping(manifest.get("contractVersions"), "contractVersions")
    missing_contracts = sorted(set(csv_filenames) - set(contract_versions))
    unexpected_contracts = sorted(set(contract_versions) - set(csv_filenames))
    if missing_contracts or unexpected_contracts:
        details = []
        if missing_contracts:
            details.append(f"missing {', '.join(missing_contracts)}")
        if unexpected_contracts:
            details.append(f"unexpected {', '.join(unexpected_contracts)}")
        raise ReferencePackageError(
            "Reference manifest contractVersions must cover exactly the normalized CSV files: "
            + "; ".join(details)
            + "."
        )
    for filename in csv_filenames:
        version = _manifest_integer(contract_versions[filename], f"contractVersions.{filename}")
        if version != package_version:
            raise ReferencePackageError(
                f"Reference file {filename} uses unsupported contract version {version}; "
                f"package version {package_version} requires contract version {package_version}."
            )

    formula_version = _formula_contract_version(formula)
    if (
        formula_version not in SUPPORTED_REFERENCE_CONTRACT_VERSIONS
        or formula_version > package_version
    ):
        raise ReferencePackageError(
            "Formula reference contract version is incompatible with the reference package: "
            f"formula requires {formula_version}, package provides "
            f"{package_version}."
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

    if package_version >= 2:
        _manifest_text(manifest.get("formulaVersion"), "formulaVersion")
        _manifest_hash(manifest.get("formulaDocumentHash"), "formulaDocumentHash")

    for filename in expected_data_files:
        entry = _manifest_mapping(file_entries[filename], f"files.{filename}")
        _manifest_integer(entry.get("rowCount"), f"files.{filename}.rowCount", minimum=0)
        _manifest_hash(entry.get("sha256"), f"files.{filename}.sha256")
    declared_content_hash = _manifest_hash(manifest.get("contentHash"), "contentHash")
    return file_entries, declared_content_hash


def _verified_hashes(
    directory: Path,
    filenames: tuple[str, ...],
    file_entries: Mapping[str, Any],
) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for filename in filenames:
        path = directory / filename
        if not path.is_file():
            raise ReferencePackageError(
                f"Reference package is missing required file {filename}: {path}"
            )
        actual = sha256_file(path)
        expected = str(_manifest_mapping(file_entries[filename], f"files.{filename}")["sha256"])
        if actual != expected:
            raise ReferencePackageError(
                f"Reference package file {filename} SHA-256 mismatch: "
                f"expected {expected}, found {actual}."
            )
        hashes[filename] = actual
    return hashes


def _audit_row_count(path: Path) -> int:
    try:
        with path.open("r", encoding="utf-8") as handle:
            audit = json.load(handle)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ReferencePackageError(
            f"Unable to parse reference package file audit.json: {error}"
        ) from error
    if not isinstance(audit, Mapping):
        raise ReferencePackageError("Reference package file audit.json must be an object.")
    return sum(len(value) for value in audit.values() if isinstance(value, list))


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
    directory: Path,
    contract: Mapping[str, Any],
    file_entries: Mapping[str, Any],
) -> dict[str, pd.DataFrame]:
    tables: dict[str, pd.DataFrame] = {}
    for filename, file_contract in contract["files"].items():
        frame = pd.read_csv(
            directory / filename,
            dtype=_pandas_dtypes(file_contract),
            keep_default_na=False,
            na_values=[""],
        )
        expected_count = _manifest_integer(
            _manifest_mapping(file_entries[filename], f"files.{filename}").get("rowCount"),
            f"files.{filename}.rowCount",
            minimum=0,
        )
        if len(frame) != expected_count:
            raise ReferencePackageError(
                f"Reference package file {filename} rowCount mismatch: "
                f"manifest declares {expected_count}, found {len(frame)}."
            )
        tables[filename] = frame
    return tables


def _validate_attribute_formula_version(
    tables: Mapping[str, pd.DataFrame],
    manifest: Mapping[str, Any],
    package_version: int,
) -> None:
    if package_version < 2:
        return
    expected = _manifest_text(manifest.get("formulaVersion"), "formulaVersion")
    values = {
        str(value)
        for value in tables["player_attributes.csv"]["formulaVersion"]
        if not pd.isna(value)
    }
    if values != {expected}:
        found = ", ".join(sorted(values)) if values else "<none>"
        raise ReferencePackageError(
            "Reference player_attributes.csv formulaVersion values must all match the "
            f"manifest formulaVersion {expected!r}; found {found}."
        )


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
    contract = load_reference_contract(package_version)
    csv_filenames = tuple(str(filename) for filename in contract["files"])
    file_entries, declared_content_hash = _validate_manifest(
        directory, manifest, csv_filenames, formula, package_version
    )
    data_filenames = (*csv_filenames, AUDIT_FILENAME)
    initial_hashes = _verified_hashes(directory, data_filenames, file_entries)
    actual_content_hash = content_hash(initial_hashes)
    if actual_content_hash != declared_content_hash:
        raise ReferencePackageError(
            "Reference package contentHash mismatch: "
            f"expected {declared_content_hash}, found {actual_content_hash}."
        )

    try:
        validate_reference_package(directory, contract=contract)
    except ContractValidationError as error:
        raise ReferencePackageError(
            f"Reference package contract validation failed: {error}"
        ) from error

    tables = _read_typed_tables(directory, contract, file_entries)
    _validate_attribute_formula_version(tables, manifest, package_version)
    audit_count = _audit_row_count(directory / AUDIT_FILENAME)
    expected_audit_count = _manifest_integer(
        _manifest_mapping(file_entries[AUDIT_FILENAME], "files.audit.json").get("rowCount"),
        "files.audit.json.rowCount",
        minimum=0,
    )
    if audit_count != expected_audit_count:
        raise ReferencePackageError(
            "Reference package file audit.json rowCount mismatch: "
            f"manifest declares {expected_audit_count}, found {audit_count}."
        )

    final_hashes = _verified_hashes(directory, data_filenames, file_entries)
    if final_hashes != initial_hashes:
        changed = next(
            filename
            for filename in data_filenames
            if final_hashes[filename] != initial_hashes[filename]
        )
        raise ReferencePackageError(
            f"Reference package file {changed} changed while it was being read."
        )
    final_content_hash = content_hash(final_hashes)
    if final_content_hash != declared_content_hash:
        raise ReferencePackageError(
            "Reference package contentHash changed while it was being read: "
            f"expected {declared_content_hash}, found {final_content_hash}."
        )

    players = tables["players.csv"]
    seasons = tables["player_seasons.csv"]
    source_ids = tables["player_source_ids.csv"]
    forbidden_player_ids = set(_non_null_strings(players["playerId"], casefold=True))
    forbidden_player_ids.update(
        _non_null_strings(source_ids["sourcePlayerId"], casefold=True)
    )
    return LoadedReferencePackage(
        path=directory,
        manifest=manifest,
        content_hash=final_content_hash,
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
