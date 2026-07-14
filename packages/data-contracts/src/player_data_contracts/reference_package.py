"""Integrity-checked loading for published normalized reference packages."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from player_data_contracts.csv_contract import validate_csv_package
from player_data_contracts.io import sha256_file
from player_data_contracts.package import content_hash
from player_data_contracts.reference import (
    SUPPORTED_REFERENCE_CONTRACT_VERSIONS,
    load_reference_contract,
)
from player_data_contracts.validation import ContractValidationError

AUDIT_FILENAME: Final = "audit.json"
MANIFEST_FILENAME: Final = "manifest.json"
REFERENCE_MANIFEST_VERSION: Final = 1
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


class ReferencePackageIntegrityError(ValueError):
    """Raised when a published reference package cannot be trusted or loaded."""


@dataclass(frozen=True)
class LoadedReferencePackageTables:
    """A validated package identity and its contract-normalized CSV rows."""

    path: Path
    manifest: Mapping[str, Any]
    package_version: int
    content_hash: str
    contract: Mapping[str, Any]
    tables: Mapping[str, list[dict[str, object]]]


def _manifest_mapping(value: object, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ReferencePackageIntegrityError(
            f"Reference manifest field {field} must be an object."
        )
    return value


def _manifest_integer(value: object, field: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ReferencePackageIntegrityError(
            f"Reference manifest field {field} must be an integer."
        )
    if minimum is not None and value < minimum:
        raise ReferencePackageIntegrityError(
            f"Reference manifest field {field} must be at least {minimum}."
        )
    return value


def _manifest_hash(value: object, field: str) -> str:
    if not isinstance(value, str) or _SHA256_PATTERN.fullmatch(value) is None:
        raise ReferencePackageIntegrityError(
            f"Reference manifest field {field} must be a lowercase SHA-256 hash."
        )
    return value


def _manifest_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReferencePackageIntegrityError(
            f"Reference manifest field {field} must be a non-empty string."
        )
    return value


def _read_manifest(directory: Path) -> dict[str, Any]:
    manifest_path = directory / MANIFEST_FILENAME
    if not manifest_path.is_file():
        raise ReferencePackageIntegrityError(
            f"Reference package is missing required file {MANIFEST_FILENAME}: {manifest_path}"
        )
    try:
        with manifest_path.open("r", encoding="utf-8") as handle:
            manifest = json.load(handle)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ReferencePackageIntegrityError(
            f"Unable to parse reference package file {MANIFEST_FILENAME}: {error}"
        ) from error
    if not isinstance(manifest, dict):
        raise ReferencePackageIntegrityError(
            f"Reference package file {MANIFEST_FILENAME} must be an object."
        )
    return manifest


def _allowed_versions(values: Sequence[int]) -> tuple[int, ...]:
    versions = tuple(values)
    if (
        not versions
        or any(isinstance(version, bool) or not isinstance(version, int) for version in versions)
        or len(set(versions)) != len(versions)
    ):
        raise ReferencePackageIntegrityError(
            "Reference package allowed_versions must contain unique integer versions."
        )
    unsupported = set(versions) - set(SUPPORTED_REFERENCE_CONTRACT_VERSIONS)
    if unsupported:
        joined = ", ".join(str(version) for version in sorted(unsupported))
        raise ReferencePackageIntegrityError(
            f"Reference package allowed_versions contains unsupported versions: {joined}."
        )
    return versions


def _package_version(
    manifest: Mapping[str, Any], allowed_versions: tuple[int, ...]
) -> int:
    package_version = _manifest_integer(manifest.get("packageVersion"), "packageVersion")
    if package_version not in allowed_versions:
        supported = ", ".join(str(version) for version in allowed_versions)
        noun = "version is" if len(allowed_versions) == 1 else "versions are"
        raise ReferencePackageIntegrityError(
            "Reference manifest uses unsupported packageVersion "
            f"{package_version}; supported {noun} {supported}."
        )
    return package_version


def _validate_manifest(
    directory: Path,
    manifest: Mapping[str, Any],
    contract: Mapping[str, Any],
    package_version: int,
) -> tuple[Mapping[str, Any], tuple[str, ...], str]:
    manifest_version = _manifest_integer(manifest.get("manifestVersion"), "manifestVersion")
    if manifest_version != REFERENCE_MANIFEST_VERSION:
        raise ReferencePackageIntegrityError(
            "Reference manifest uses unsupported manifestVersion "
            f"{manifest_version}; supported version is {REFERENCE_MANIFEST_VERSION}."
        )
    if manifest.get("packageType") != "reference":
        raise ReferencePackageIntegrityError(
            "Reference manifest field packageType must equal 'reference'; "
            f"found {manifest.get('packageType')!r}."
        )

    csv_filenames = tuple(str(filename) for filename in contract["files"])
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
        raise ReferencePackageIntegrityError(
            "Reference manifest files must contain exactly the normalized CSV and audit files: "
            + "; ".join(details)
            + "."
        )

    actual_files = {entry.name for entry in directory.iterdir()}
    expected_files = {*expected_data_files, MANIFEST_FILENAME}
    missing_files = sorted(expected_files - actual_files)
    unexpected_files = sorted(actual_files - expected_files)
    if missing_files or unexpected_files:
        details = []
        if missing_files:
            details.append(f"missing {', '.join(missing_files)}")
        if unexpected_files:
            details.append(f"unexpected {', '.join(unexpected_files)}")
        raise ReferencePackageIntegrityError(
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
        raise ReferencePackageIntegrityError(
            "Reference manifest contractVersions must cover exactly the normalized CSV files: "
            + "; ".join(details)
            + "."
        )
    for filename in csv_filenames:
        version = _manifest_integer(
            contract_versions[filename], f"contractVersions.{filename}"
        )
        if version != package_version:
            raise ReferencePackageIntegrityError(
                f"Reference file {filename} uses unsupported contract version {version}; "
                f"package version {package_version} requires contract version {package_version}."
            )

    if package_version >= 2:
        _manifest_text(manifest.get("formulaVersion"), "formulaVersion")
        _manifest_hash(manifest.get("formulaDocumentHash"), "formulaDocumentHash")

    for filename in expected_data_files:
        entry = _manifest_mapping(file_entries[filename], f"files.{filename}")
        _manifest_integer(entry.get("rowCount"), f"files.{filename}.rowCount", minimum=0)
        _manifest_hash(entry.get("sha256"), f"files.{filename}.sha256")
    declared_content_hash = _manifest_hash(manifest.get("contentHash"), "contentHash")
    return file_entries, expected_data_files, declared_content_hash


def _verified_hashes(
    directory: Path,
    filenames: Sequence[str],
    file_entries: Mapping[str, Any],
) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for filename in filenames:
        path = directory / filename
        if not path.is_file():
            raise ReferencePackageIntegrityError(
                f"Reference package is missing required file {filename}: {path}"
            )
        actual = sha256_file(path)
        expected = str(
            _manifest_mapping(file_entries[filename], f"files.{filename}")["sha256"]
        )
        if actual != expected:
            raise ReferencePackageIntegrityError(
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
        raise ReferencePackageIntegrityError(
            f"Unable to parse reference package file {AUDIT_FILENAME}: {error}"
        ) from error
    if not isinstance(audit, Mapping):
        raise ReferencePackageIntegrityError(
            f"Reference package file {AUDIT_FILENAME} must be an object."
        )
    return sum(len(value) for value in audit.values() if isinstance(value, list))


def _validate_row_counts(
    tables: Mapping[str, Sequence[Mapping[str, object]]],
    file_entries: Mapping[str, Any],
) -> None:
    for filename, rows in tables.items():
        expected = _manifest_integer(
            _manifest_mapping(file_entries[filename], f"files.{filename}").get("rowCount"),
            f"files.{filename}.rowCount",
            minimum=0,
        )
        if len(rows) != expected:
            raise ReferencePackageIntegrityError(
                f"Reference package file {filename} rowCount mismatch: "
                f"manifest declares {expected}, found {len(rows)}."
            )


def _validate_attribute_formula_version(
    tables: Mapping[str, Sequence[Mapping[str, object]]],
    manifest: Mapping[str, Any],
    package_version: int,
) -> None:
    if package_version < 2:
        return
    expected = _manifest_text(manifest.get("formulaVersion"), "formulaVersion")
    values = {
        str(row["formulaVersion"])
        for row in tables["player_attributes.csv"]
        if row["formulaVersion"] is not None
    }
    if values != {expected}:
        found = ", ".join(sorted(values)) if values else "<none>"
        raise ReferencePackageIntegrityError(
            "Reference player_attributes.csv formulaVersion values must all match the "
            f"manifest formulaVersion {expected!r}; found {found}."
        )


def load_reference_package_tables(
    path: str | Path,
    allowed_versions: Sequence[int] = (2,),
) -> LoadedReferencePackageTables:
    """Load a complete published reference package after integrity and contract checks."""
    directory = Path(path).expanduser().resolve()
    if not directory.is_dir():
        raise ReferencePackageIntegrityError(
            f"Reference package directory does not exist: {directory}"
        )

    versions = _allowed_versions(allowed_versions)
    manifest = _read_manifest(directory)
    package_version = _package_version(manifest, versions)
    contract = load_reference_contract(package_version)
    file_entries, data_filenames, declared_content_hash = _validate_manifest(
        directory, manifest, contract, package_version
    )

    initial_hashes = _verified_hashes(directory, data_filenames, file_entries)
    actual_content_hash = content_hash(initial_hashes)
    if actual_content_hash != declared_content_hash:
        raise ReferencePackageIntegrityError(
            "Reference package contentHash mismatch: "
            f"expected {declared_content_hash}, found {actual_content_hash}."
        )

    try:
        tables = validate_csv_package(
            directory,
            contract=contract,
            contract_name="Reference",
            contract_version=package_version,
        )
    except ContractValidationError as error:
        raise ReferencePackageIntegrityError(
            f"Reference package contract validation failed: {error}"
        ) from error
    _validate_row_counts(tables, file_entries)
    _validate_attribute_formula_version(tables, manifest, package_version)

    audit_count = _audit_row_count(directory / AUDIT_FILENAME)
    expected_audit_count = _manifest_integer(
        _manifest_mapping(file_entries[AUDIT_FILENAME], "files.audit.json").get("rowCount"),
        "files.audit.json.rowCount",
        minimum=0,
    )
    if audit_count != expected_audit_count:
        raise ReferencePackageIntegrityError(
            f"Reference package file {AUDIT_FILENAME} rowCount mismatch: "
            f"manifest declares {expected_audit_count}, found {audit_count}."
        )

    final_hashes = _verified_hashes(directory, data_filenames, file_entries)
    if final_hashes != initial_hashes:
        changed = next(
            filename
            for filename in data_filenames
            if final_hashes[filename] != initial_hashes[filename]
        )
        raise ReferencePackageIntegrityError(
            f"Reference package file {changed} changed while it was being read."
        )
    final_content_hash = content_hash(final_hashes)
    if final_content_hash != declared_content_hash:
        raise ReferencePackageIntegrityError(
            "Reference package contentHash changed while it was being read: "
            f"expected {declared_content_hash}, found {final_content_hash}."
        )

    return LoadedReferencePackageTables(
        path=directory,
        manifest=manifest,
        package_version=package_version,
        content_hash=final_content_hash,
        contract=contract,
        tables=tables,
    )


__all__ = [
    "LoadedReferencePackageTables",
    "ReferencePackageIntegrityError",
    "load_reference_package_tables",
]
