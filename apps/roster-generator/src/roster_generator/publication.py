from __future__ import annotations

import csv
import json
import os
import re
import shutil
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any
from uuid import uuid4

from player_data_contracts.io import sha256_file
from player_data_contracts.package import content_hash
from player_data_contracts.roster import (
    ROSTER_CONTRACT_VERSION,
    load_roster_contract,
    validate_roster_package,
    validate_roster_tables,
)
from player_data_contracts.validation import ContractValidationError

from roster_generator.generator import GeneratedRoster
from roster_generator.reference_package import LoadedReferencePackage

CSV_FILENAMES = (
    "players.csv",
    "player_stats.csv",
    "player_attributes.csv",
)
MANIFEST_FILENAME = "manifest.json"
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


class RosterPublicationError(ValueError):
    """Raised when a roster package cannot be validated or published safely."""


def _manifest_integer(value: object, field: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise RosterPublicationError(f"Roster manifest field {field} must be an integer")
    if minimum is not None and value < minimum:
        raise RosterPublicationError(
            f"Roster manifest field {field} must be at least {minimum}"
        )
    return value


def _contract_headers(contract: Mapping[str, Any], filename: str) -> tuple[str, ...]:
    try:
        return tuple(column["name"] for column in contract["files"][filename]["columns"])
    except (KeyError, TypeError) as error:
        raise RosterPublicationError(
            f"Roster contract is missing columns for {filename}"
        ) from error


def _csv_value(value: object) -> object:
    return "" if value is None else value


def _write_csv(
    path: Path,
    rows: Sequence[Mapping[str, object]],
    headers: tuple[str, ...],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            unexpected = set(row) - set(headers)
            if unexpected:
                raise RosterPublicationError(
                    f"{path.name} contains fields outside roster contract version 1: "
                    f"{', '.join(sorted(unexpected))}"
                )
            writer.writerow({header: _csv_value(row.get(header)) for header in headers})


def _write_json(path: Path, payload: object) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False, sort_keys=True)
        handle.write("\n")


def _sort_rows(filename: str, rows: Sequence[Mapping[str, object]]) -> list[Mapping[str, object]]:
    fields = ("playerId", "season") if filename == "player_stats.csv" else ("playerId",)
    return sorted(rows, key=lambda row: tuple(str(row[field]) for field in fields))


def _identity_leak_scan(
    tables: Mapping[str, Sequence[Mapping[str, object]]],
    reference: LoadedReferencePackage,
) -> None:
    forbidden_fields = {"source", "reference", "template", "teamid", "crosswalk", "rowindex"}
    for filename, rows in tables.items():
        for row_index, row in enumerate(rows, start=1):
            for field in row:
                normalized_field = field.replace("_", "").casefold()
                if any(term in normalized_field for term in forbidden_fields):
                    raise RosterPublicationError(
                        f"{filename} row {row_index} exposes forbidden identity field {field}"
                    )

    for row_index, row in enumerate(tables["players.csv"], start=1):
        player_id = str(row["playerId"]).casefold()
        if player_id in reference.forbidden_player_ids:
            raise RosterPublicationError(
                f"players.csv row {row_index} reuses a reference player ID"
            )
        display_name = str(row["displayName"]).strip().casefold()
        if display_name in reference.forbidden_names:
            raise RosterPublicationError(
                f"players.csv row {row_index} reuses a reference player name"
            )
        text_values = {
            str(row[field]).strip().casefold()
            for field in ("playerId", "displayName", "firstName", "lastName")
        }
        if text_values & reference.forbidden_player_ids:
            raise RosterPublicationError(
                f"players.csv row {row_index} exposes a reference player ID"
            )
        if text_values & reference.forbidden_team_ids:
            raise RosterPublicationError(
                f"players.csv row {row_index} exposes a reference team ID"
            )


def _validate_formula_versions(
    rows: Sequence[Mapping[str, object]], formula_version: object
) -> str:
    if not isinstance(formula_version, str) or not formula_version.strip():
        raise RosterPublicationError("Formula version must be non-empty text")
    attribute_versions = {str(row["formulaVersion"]) for row in rows}
    if attribute_versions != {formula_version}:
        raise RosterPublicationError(
            "player_attributes.csv formulaVersion values must all match the published "
            f"formula version {formula_version!r}; found {sorted(attribute_versions)!r}"
        )
    return formula_version


def _manifest(
    generated: GeneratedRoster,
    reference: LoadedReferencePackage,
    formula_version: str,
    formula_hash: str,
    stage: Path,
) -> dict[str, object]:
    file_hashes = {filename: sha256_file(stage / filename) for filename in CSV_FILENAMES}
    return {
        "manifestVersion": 1,
        "packageType": "roster",
        "packageVersion": 1,
        "contractVersions": {
            filename: ROSTER_CONTRACT_VERSION for filename in CSV_FILENAMES
        },
        "referencePackageHash": reference.content_hash,
        "formulaVersion": formula_version,
        "formulaHash": formula_hash,
        "seed": generated.seed,
        "configurationHash": generated.configuration_hash,
        "files": {
            filename: {
                "rowCount": len(generated.tables[filename]),
                "sha256": file_hashes[filename],
            }
            for filename in CSV_FILENAMES
        },
        "contentHash": content_hash(file_hashes),
    }


def validate_published_roster_package(directory: str | Path) -> dict[str, object]:
    package_dir = Path(directory)
    try:
        validate_roster_package(package_dir)
    except ContractValidationError as error:
        raise RosterPublicationError(
            f"Roster package contract validation failed: {error}"
        ) from error
    expected_entries = {*CSV_FILENAMES, MANIFEST_FILENAME}
    actual_entries = {entry.name for entry in package_dir.iterdir()}
    if actual_entries != expected_entries:
        missing = sorted(expected_entries - actual_entries)
        unexpected = sorted(actual_entries - expected_entries)
        details: list[str] = []
        if missing:
            details.append(f"missing {', '.join(missing)}")
        if unexpected:
            details.append(f"unexpected {', '.join(unexpected)}")
        raise RosterPublicationError(
            "Roster package directory must contain exactly the three CSVs and manifest: "
            + "; ".join(details)
        )
    manifest_path = package_dir / MANIFEST_FILENAME
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise RosterPublicationError(f"Roster package is missing {manifest_path}") from error
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RosterPublicationError(
            f"Roster manifest is invalid: {manifest_path}: {error}"
        ) from error
    if not isinstance(manifest, dict):
        raise RosterPublicationError("Roster manifest must be an object")
    manifest_version = _manifest_integer(manifest.get("manifestVersion"), "manifestVersion")
    if manifest_version != 1:
        raise RosterPublicationError(
            f"Unsupported roster manifest version: {manifest_version!r}"
        )
    package_version = _manifest_integer(manifest.get("packageVersion"), "packageVersion")
    if manifest.get("packageType") != "roster" or package_version != 1:
        raise RosterPublicationError(
            "Roster manifest declares an incompatible package type/version"
        )
    contract_versions = manifest.get("contractVersions")
    if not isinstance(contract_versions, dict) or set(contract_versions) != set(CSV_FILENAMES):
        raise RosterPublicationError("Roster manifest has incompatible CSV contract versions")
    for filename in CSV_FILENAMES:
        version = _manifest_integer(
            contract_versions[filename], f"contractVersions.{filename}"
        )
        if version != ROSTER_CONTRACT_VERSION:
            raise RosterPublicationError(
                f"Roster manifest has incompatible contract version for {filename}: {version}"
            )
    files = manifest.get("files")
    if not isinstance(files, dict) or set(files) != set(CSV_FILENAMES):
        raise RosterPublicationError("Roster manifest must describe exactly the three roster CSVs")

    file_hashes: dict[str, str] = {}
    for filename in CSV_FILENAMES:
        entry = files[filename]
        if not isinstance(entry, dict):
            raise RosterPublicationError(f"Roster manifest entry for {filename} must be an object")
        path = package_dir / filename
        actual_hash = sha256_file(path)
        if entry.get("sha256") != actual_hash:
            raise RosterPublicationError(f"Roster package content hash mismatch for {filename}")
        with path.open("r", encoding="utf-8", newline="") as handle:
            row_count = max(0, sum(1 for _row in csv.reader(handle)) - 1)
        declared_row_count = _manifest_integer(
            entry.get("rowCount"), f"files.{filename}.rowCount", minimum=0
        )
        if declared_row_count != row_count:
            raise RosterPublicationError(f"Roster package row count mismatch for {filename}")
        file_hashes[filename] = actual_hash
    if manifest.get("contentHash") != content_hash(file_hashes):
        raise RosterPublicationError("Roster package aggregate content hash mismatch")
    for field in ("referencePackageHash", "formulaHash", "configurationHash"):
        value = manifest.get(field)
        if not isinstance(value, str) or _SHA256_PATTERN.fullmatch(value) is None:
            raise RosterPublicationError(
                f"Roster manifest field {field} must be a lowercase SHA-256 hash"
            )
    formula_version = manifest.get("formulaVersion")
    if not isinstance(formula_version, str) or not formula_version.strip():
        raise RosterPublicationError(
            "Roster manifest field formulaVersion must be non-empty text"
        )
    with (package_dir / "player_attributes.csv").open(
        "r", encoding="utf-8", newline=""
    ) as handle:
        _validate_formula_versions(list(csv.DictReader(handle)), formula_version)
    seed = manifest.get("seed")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise RosterPublicationError("Roster manifest field seed must be an integer")
    return manifest


def _remove_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink(missing_ok=True)


def _replace_package(stage: Path, destination: Path) -> None:
    backup = destination.parent / f".{destination.name}.backup-{uuid4().hex}"
    had_destination = destination.exists() or destination.is_symlink()
    if had_destination:
        os.replace(destination, backup)
    try:
        os.replace(stage, destination)
    except Exception:
        if had_destination and backup.exists():
            os.replace(backup, destination)
        raise
    if had_destination:
        _remove_path(backup)


def publish_roster_package(
    generated: GeneratedRoster,
    reference: LoadedReferencePackage,
    destination: str | Path,
    *,
    formula_version: str,
    formula_hash: str,
) -> Path:
    contract = load_roster_contract()
    if tuple(contract.get("files", {})) != CSV_FILENAMES:
        raise RosterPublicationError(
            "Roster contract must define exactly the three normalized CSVs in publication order"
        )
    validate_roster_tables(generated.tables, contract=contract)
    _identity_leak_scan(generated.tables, reference)
    _validate_formula_versions(generated.tables["player_attributes.csv"], formula_version)

    output_path = Path(destination).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(
        tempfile.mkdtemp(prefix=f".{output_path.name}.tmp-", dir=output_path.parent)
    )
    try:
        for filename in CSV_FILENAMES:
            _write_csv(
                stage / filename,
                _sort_rows(filename, generated.tables[filename]),
                _contract_headers(contract, filename),
            )
        validate_roster_package(stage, contract=contract)
        _write_json(
            stage / MANIFEST_FILENAME,
            _manifest(generated, reference, formula_version, formula_hash, stage),
        )
        validate_published_roster_package(stage)
        _replace_package(stage, output_path)
    finally:
        if stage.exists():
            _remove_path(stage)
    return output_path
