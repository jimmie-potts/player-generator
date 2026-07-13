from __future__ import annotations

import csv
import json
import os
import shutil
import tempfile
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from player_data_contracts.io import sha256_file
from player_data_contracts.package import content_hash
from player_data_contracts.reference import load_reference_contract, validate_reference_package

from reference_data_app.canonical import CanonicalBundle, normalize_registered_sources
from reference_data_app.config import resolve_path

CSV_FILENAMES = (
    "players.csv",
    "player_seasons.csv",
    "player_stats.csv",
    "player_advanced_stats.csv",
    "player_source_ids.csv",
    "sources.csv",
)
AUDIT_FILENAME = "audit.json"
MANIFEST_FILENAME = "manifest.json"


class PublicationError(ValueError):
    """Raised when a normalized reference package cannot be published safely."""


def _utc_timestamp(created_at: datetime | None) -> str:
    value = created_at or datetime.now(timezone.utc)
    if value.tzinfo is None:
        raise PublicationError("Package creation timestamp must include a timezone.")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _contract_headers(contract: Mapping[str, Any], filename: str) -> tuple[str, ...]:
    try:
        return tuple(column["name"] for column in contract["files"][filename]["columns"])
    except (KeyError, TypeError) as error:
        raise PublicationError(f"Reference contract is missing columns for {filename}") from error


def _bundle_tables(bundle: CanonicalBundle) -> dict[str, list[dict[str, Any]]]:
    sources: list[dict[str, Any]] = []
    for source in bundle.sources:
        published_source = dict(source)
        published_source.pop("inputPath", None)
        sources.append(published_source)
    return {
        "players.csv": [dict(row) for row in bundle.players],
        "player_seasons.csv": [dict(row) for row in bundle.player_seasons],
        "player_stats.csv": [dict(row) for row in bundle.player_stats],
        "player_advanced_stats.csv": [dict(row) for row in bundle.player_advanced_stats],
        "player_source_ids.csv": [dict(row) for row in bundle.player_source_ids],
        "sources.csv": sources,
    }


def _sort_rows(filename: str, rows: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    sort_fields = {
        "players.csv": ("playerId",),
        "player_seasons.csv": ("playerSeasonId",),
        "player_stats.csv": ("playerSeasonId",),
        "player_advanced_stats.csv": ("playerSeasonId",),
        "player_source_ids.csv": ("playerId", "sourceType", "sourcePlayerId"),
        "sources.csv": ("sourceId",),
    }[filename]
    return sorted(rows, key=lambda row: tuple(str(row.get(field, "")) for field in sort_fields))


def _csv_value(value: object) -> object:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


def _write_csv(
    path: Path,
    rows: Sequence[Mapping[str, Any]],
    headers: tuple[str, ...],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            unexpected = set(row) - set(headers)
            if unexpected:
                raise PublicationError(
                    f"{path.name} row contains fields outside contract version 1: "
                    f"{', '.join(sorted(unexpected))}"
                )
            writer.writerow({header: _csv_value(row.get(header)) for header in headers})


def _write_json(path: Path, payload: object) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False, sort_keys=True)
        handle.write("\n")


def _audit_row_count(audit: Mapping[str, object]) -> int:
    return sum(len(value) for value in audit.values() if isinstance(value, list))


def _manifest(
    *,
    contract: Mapping[str, Any],
    bundle: CanonicalBundle,
    stage: Path,
    row_counts: Mapping[str, int],
    created_at: str,
) -> dict[str, Any]:
    file_hashes = {
        filename: sha256_file(stage / filename)
        for filename in (*CSV_FILENAMES, AUDIT_FILENAME)
    }
    files = {
        filename: {
            "rowCount": row_counts[filename],
            "sha256": file_hashes[filename],
        }
        for filename in (*CSV_FILENAMES, AUDIT_FILENAME)
    }
    inputs = sorted(
        (
            {
                "sourceId": source["sourceId"],
                "sha256": source["sha256"],
                "adapterVersion": source["adapterVersion"],
            }
            for source in bundle.sources
        ),
        key=lambda source: str(source["sourceId"]),
    )
    contract_version = int(contract["contractVersion"])
    return {
        "manifestVersion": 1,
        "packageType": "reference",
        "packageVersion": 1,
        "createdAt": created_at,
        "contractVersions": {
            filename: contract_version for filename in CSV_FILENAMES
        },
        "inputs": inputs,
        "files": files,
        "contentHash": content_hash(file_hashes),
    }


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


def publish_reference_package(
    config: Mapping[str, Any],
    output_path: str | Path | None = None,
    *,
    created_at: datetime | None = None,
) -> Path:
    contract = load_reference_contract()
    contract_filenames = tuple(contract.get("files", {}))
    if contract_filenames != CSV_FILENAMES:
        raise PublicationError(
            "Reference contract must define exactly the six normalized CSVs in publication order"
        )

    bundle = normalize_registered_sources(config)
    tables = _bundle_tables(bundle)
    destination = (
        Path(output_path).expanduser().resolve()
        if output_path is not None
        else resolve_path(dict(config), "reference_package_dir").resolve()
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(
        tempfile.mkdtemp(prefix=f".{destination.name}.tmp-", dir=destination.parent)
    )
    try:
        row_counts: dict[str, int] = {}
        for filename in CSV_FILENAMES:
            rows = _sort_rows(filename, tables[filename])
            _write_csv(stage / filename, rows, _contract_headers(contract, filename))
            row_counts[filename] = len(rows)

        _write_json(stage / AUDIT_FILENAME, bundle.audit)
        row_counts[AUDIT_FILENAME] = _audit_row_count(bundle.audit)

        validate_reference_package(stage, contract=contract)
        manifest = _manifest(
            contract=contract,
            bundle=bundle,
            stage=stage,
            row_counts=row_counts,
            created_at=_utc_timestamp(created_at),
        )
        _write_json(stage / MANIFEST_FILENAME, manifest)
        _replace_package(stage, destination)
    finally:
        if stage.exists():
            _remove_path(stage)
    return destination
