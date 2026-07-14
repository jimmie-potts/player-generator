from __future__ import annotations

import csv
import json
import math
import os
import shutil
import tempfile
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd
from player_attribute_engine import (
    FormulaDocument,
    evaluate_player_attributes,
    load_formula_snapshot,
)
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
    "player_attributes.csv",
    "player_source_ids.csv",
    "sources.csv",
)
AUDIT_FILENAME = "audit.json"
MANIFEST_FILENAME = "manifest.json"
REFERENCE_PACKAGE_VERSION = 2


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


def _formula_output_fields(formula: FormulaDocument) -> tuple[str, ...]:
    return tuple(str(field) for field in formula.output_fields)


def _season_schedule_key(season: object) -> str | None:
    if season is None or isinstance(season, bool):
        return None
    try:
        numeric = float(season)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric) or not numeric.is_integer():
        return None
    return str(int(numeric))


def _supports_scheduled_ratio_metrics(season: object, formula: FormulaDocument) -> bool:
    scheduled_metrics = tuple(
        metric for metric in formula.metrics.values() if metric.kind == "scheduledRatio"
    )
    if not scheduled_metrics:
        return True
    season_key = _season_schedule_key(season)
    if season_key is None:
        # Invalid cohort keys still go through the evaluator and contract validator so their
        # underlying data failure is not disguised as an unsupported historical season.
        return True
    return all(season_key in metric.schedule for metric in scheduled_metrics)


def _unsupported_cohort_rows(
    cohort: pd.DataFrame,
    formula: FormulaDocument,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for index in cohort.index:
        row = {field: None for field in formula.output_fields}
        row["playerId"] = cohort.at[index, "playerId"]
        row["formulaVersion"] = formula.formula_version
        rows.append(row)
    return rows


def _attribute_input_frame(
    bundle: CanonicalBundle,
    contract: Mapping[str, Any],
) -> pd.DataFrame:
    identity = ["playerSeasonId", "playerId", "season"]

    def frame(filename: str, rows: Sequence[Mapping[str, Any]]) -> pd.DataFrame:
        return pd.DataFrame(rows, columns=_contract_headers(contract, filename))

    seasons = frame("player_seasons.csv", bundle.player_seasons)
    stats = frame("player_stats.csv", bundle.player_stats)
    advanced = frame("player_advanced_stats.csv", bundle.player_advanced_stats)
    try:
        joined = seasons.merge(
            stats,
            on=identity,
            how="left",
            sort=False,
            validate="one_to_one",
        ).merge(
            advanced,
            on=identity,
            how="left",
            sort=False,
            validate="one_to_one",
        )
    except pd.errors.MergeError as error:
        raise PublicationError(
            "Canonical player-season, stats, and advanced-stat rows must have one-to-one keys"
        ) from error
    return joined.sort_values(["season", "playerSeasonId"], kind="stable").reset_index(drop=True)


def _attribute_rows(
    bundle: CanonicalBundle,
    contract: Mapping[str, Any],
    formula: FormulaDocument,
) -> list[dict[str, Any]]:
    headers = _contract_headers(contract, "player_attributes.csv")
    expected_formula_fields = tuple(
        field for field in headers if field not in {"playerSeasonId", "season"}
    )
    actual_formula_fields = _formula_output_fields(formula)
    if actual_formula_fields != expected_formula_fields:
        raise PublicationError(
            "Formula output fields do not match reference contract version 2 "
            f"player_attributes.csv: expected {expected_formula_fields!r}, "
            f"found {actual_formula_fields!r}"
        )

    joined = _attribute_input_frame(bundle, contract)
    rows: list[dict[str, Any]] = []
    for season, cohort in joined.groupby("season", sort=True, dropna=False):
        cohort = cohort.sort_values("playerSeasonId", kind="stable").reset_index(drop=True)
        evaluated = (
            evaluate_player_attributes(cohort, formula).rows
            if _supports_scheduled_ratio_metrics(season, formula)
            else _unsupported_cohort_rows(cohort, formula)
        )
        if len(evaluated) != len(cohort):
            raise PublicationError(
                "Attribute engine returned a different row count than its player-season cohort"
            )
        for index, evaluated_row in enumerate(evaluated):
            expected_player_id = cohort.at[index, "playerId"]
            if evaluated_row.get("playerId") != expected_player_id:
                raise PublicationError(
                    "Attribute engine output playerId/order mismatch for "
                    f"playerSeasonId {cohort.at[index, 'playerSeasonId']!r}: expected "
                    f"{expected_player_id!r}, found {evaluated_row.get('playerId')!r}"
                )
            enriched = dict(evaluated_row)
            enriched.update(
                {
                    "playerSeasonId": cohort.at[index, "playerSeasonId"],
                    "playerId": cohort.at[index, "playerId"],
                    "season": cohort.at[index, "season"],
                }
            )
            rows.append({header: enriched.get(header) for header in headers})
    return sorted(rows, key=lambda row: str(row["playerSeasonId"]))


def _bundle_tables(
    bundle: CanonicalBundle,
    contract: Mapping[str, Any],
    formula: FormulaDocument,
) -> dict[str, list[dict[str, Any]]]:
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
        "player_attributes.csv": _attribute_rows(bundle, contract, formula),
        "player_source_ids.csv": [dict(row) for row in bundle.player_source_ids],
        "sources.csv": sources,
    }


def _sort_rows(filename: str, rows: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    sort_fields = {
        "players.csv": ("playerId",),
        "player_seasons.csv": ("playerSeasonId",),
        "player_stats.csv": ("playerSeasonId",),
        "player_advanced_stats.csv": ("playerSeasonId",),
        "player_attributes.csv": ("playerSeasonId",),
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
                    f"{path.name} row contains fields outside the active reference contract: "
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
    formula_version: str,
    formula_document_hash: str,
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
        "packageVersion": REFERENCE_PACKAGE_VERSION,
        "createdAt": created_at,
        "formulaVersion": formula_version,
        "formulaDocumentHash": formula_document_hash,
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
    formula_path: str | Path | None = None,
    created_at: datetime | None = None,
) -> Path:
    contract = load_reference_contract()
    contract_filenames = tuple(contract.get("files", {}))
    if contract_filenames != CSV_FILENAMES:
        raise PublicationError(
            "Reference contract version 2 must define exactly the seven normalized CSVs "
            "in publication order"
        )
    if contract.get("contractVersion") != REFERENCE_PACKAGE_VERSION:
        raise PublicationError("Reference publication requires contract version 2")

    active_formula_path = None if formula_path is None else Path(formula_path)
    formula, formula_document_hash = load_formula_snapshot(active_formula_path)
    bundle = normalize_registered_sources(config)
    tables = _bundle_tables(bundle, contract, formula)
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
            formula_version=formula.formula_version,
            formula_document_hash=formula_document_hash,
        )
        _write_json(stage / MANIFEST_FILENAME, manifest)
        _replace_package(stage, destination)
    finally:
        if stage.exists():
            _remove_path(stage)
    return destination
