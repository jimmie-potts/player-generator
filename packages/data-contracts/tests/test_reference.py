from __future__ import annotations

import copy
import csv
import json
import math
from pathlib import Path

import pytest
from player_data_contracts import (
    RATING_FIELDS,
    REFERENCE_CONTRACT_VERSION,
    ContractValidationError,
    ReferencePackageIntegrityError,
    content_hash,
    load_reference_contract,
    load_reference_package_tables,
    validate_reference_package,
    validate_reference_tables,
)
from player_data_contracts.io import sha256_file
from reference_data_app.adapters import NBA_ADVANCED_STAT_MAP, NBA_TRADITIONAL_STAT_MAP


def _headers() -> dict[str, tuple[str, ...]]:
    contract = load_reference_contract()
    return {
        file_name: tuple(column["name"] for column in file_contract["columns"])
        for file_name, file_contract in contract["files"].items()
    }


def _row(file_name: str, **values: object) -> dict[str, object]:
    row = dict.fromkeys(_headers()[file_name], None)
    row.update(values)
    return row


def _valid_tables() -> dict[str, list[dict[str, object]]]:
    player_id = "player_unicode"
    player_season_id = "playerSeason_unicode_2026"
    identity = {
        "playerSeasonId": player_season_id,
        "playerId": player_id,
        "season": 2026,
    }
    return {
        "players.csv": [
            _row(
                "players.csv",
                playerId=player_id,
                displayName="José Ñúñez",
                firstName="José",
                lastName="Ñúñez",
                birthDate="1998-04-03",
                heightInches=78.5,
                weightPounds=None,
                country="España",
                draftYear=2020,
            )
        ],
        "player_stats.csv": [
            _row(
                "player_stats.csv",
                **identity,
                teamId="team_10",
                teamAbbreviation="TST",
                age=27,
                games=72,
                starts=None,
                wins=48,
                losses=24,
                minutes=2160.5,
                points=1350,
                twoPointPercentage=0.583,
                usagePercentage=0.287,
                playerImpactEstimate=None,
            )
        ],
        "player_attributes.csv": [
            _row(
                "player_attributes.csv",
                **identity,
                insideScoring=75,
                overall=78,
                impactPercentile=0.8,
                talentTier="starter",
                formulaVersion="1.0.0",
            )
        ],
        "player_source_ids.csv": [
            _row(
                "player_source_ids.csv",
                playerId=player_id,
                sourceType="nba_playerstats",
                sourcePlayerId="101",
            )
        ],
        "sources.csv": [
            _row(
                "sources.csv",
                sourceId="nba_playerstats:sample",
                sourceType="nba_playerstats",
                originalFilename="sample.parquet",
                sha256="a" * 64,
                adapterVersion=1,
                upstreamVersion=None,
                rowCount=1,
                processedAt="2026-07-13T12:30:00Z",
                licenseStatus="test-fixture",
            )
        ],
    }


def _write_package(path: Path, tables: dict[str, list[dict[str, object]]]) -> None:
    path.mkdir()
    for file_name, rows in tables.items():
        with (path / file_name).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=_headers()[file_name], lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)


def _write_published_package(
    path: Path,
    tables: dict[str, list[dict[str, object]]],
) -> None:
    _write_package(path, tables)
    audit = {"unresolved": [], "duplicates": []}
    (path / "audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    data_files = (*tables, "audit.json")
    hashes = {filename: sha256_file(path / filename) for filename in data_files}
    manifest = {
        "manifestVersion": 1,
        "packageType": "reference",
        "packageVersion": REFERENCE_CONTRACT_VERSION,
        "createdAt": "2026-07-13T12:30:00Z",
        "formulaVersion": "1.0.0",
        "formulaDocumentHash": "b" * 64,
        "contractVersions": {
            filename: REFERENCE_CONTRACT_VERSION for filename in tables
        },
        "inputs": [],
        "files": {
            filename: {
                "rowCount": len(tables[filename]) if filename in tables else 0,
                "sha256": hashes[filename],
            }
            for filename in data_files
        },
        "contentHash": content_hash(hashes),
    }
    (path / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def test_reference_v1_is_the_only_contract_and_has_consolidated_stat_order() -> None:
    contract = load_reference_contract()

    assert contract["contractVersion"] == REFERENCE_CONTRACT_VERSION == 1
    assert tuple(contract["files"]) == (
        "players.csv",
        "player_stats.csv",
        "player_attributes.csv",
        "player_source_ids.csv",
        "sources.csv",
    )
    stats_headers = _headers()["player_stats.csv"]
    season_context = (
        "playerSeasonId",
        "playerId",
        "season",
        "teamId",
        "teamAbbreviation",
        "age",
        "games",
        "starts",
        "wins",
        "losses",
        "minutes",
    )
    assert stats_headers == (
        *season_context,
        *NBA_TRADITIONAL_STAT_MAP.values(),
        *NBA_ADVANCED_STAT_MAP.values(),
    )
    assert _headers()["player_attributes.csv"] == (
        "playerSeasonId",
        "playerId",
        "season",
        *RATING_FIELDS,
        "overall",
        "impactPercentile",
        "talentTier",
        "formulaVersion",
    )
    exact = next(
        relationship
        for relationship in contract["relationships"]
        if relationship["name"] == "referencePlayerSeasonGrain"
    )
    assert exact["files"] == ["player_stats.csv", "player_attributes.csv"]
    assert exact["columns"] == ["playerSeasonId", "playerId", "season"]


@pytest.mark.parametrize("version", [99, 0, True, 1.0])
def test_other_reference_contract_versions_are_rejected(version: object) -> None:
    with pytest.raises(
        ContractValidationError,
        match=f"Unsupported reference contract version: {version}",
    ):
        load_reference_contract(version)  # type: ignore[arg-type]


def test_valid_unicode_rows_and_optional_empty_values_are_accepted(tmp_path: Path) -> None:
    tables = _valid_tables()
    validate_reference_tables(tables)

    package_dir = tmp_path / "reference-package"
    _write_package(package_dir, tables)
    validate_reference_package(package_dir)


def test_integrity_loader_returns_v1_manifest_identity_and_typed_rows(
    tmp_path: Path,
) -> None:
    tables = _valid_tables()
    package_dir = tmp_path / "reference-package"
    _write_published_package(package_dir, tables)

    loaded = load_reference_package_tables(package_dir)

    assert loaded.path == package_dir.resolve()
    assert loaded.package_version == REFERENCE_CONTRACT_VERSION == 1
    assert loaded.content_hash == loaded.manifest["contentHash"]
    assert loaded.contract["contractVersion"] == 1
    player = loaded.tables["players.csv"][0]
    stats = loaded.tables["player_stats.csv"][0]
    source = loaded.tables["sources.csv"][0]
    assert player["draftYear"] == 2020
    assert isinstance(player["draftYear"], int)
    assert player["weightPounds"] is None
    assert stats["minutes"] == 2160.5
    assert isinstance(stats["minutes"], float)
    assert stats["usagePercentage"] == 0.287
    assert source["processedAt"] == "2026-07-13T12:30:00+00:00"


def test_integrity_loader_rejects_non_v1_package(tmp_path: Path) -> None:
    package_dir = tmp_path / "reference-package"
    _write_published_package(package_dir, _valid_tables())
    manifest_path = package_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["packageVersion"] = 99
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(
        ReferencePackageIntegrityError,
        match="unsupported packageVersion 99; supported version is 1",
    ):
        load_reference_package_tables(package_dir)


@pytest.mark.parametrize("field", ["formulaVersion", "formulaDocumentHash"])
def test_integrity_loader_requires_formula_provenance(field: str, tmp_path: Path) -> None:
    package_dir = tmp_path / "reference-package"
    _write_published_package(package_dir, _valid_tables())
    manifest_path = package_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.pop(field)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ReferencePackageIntegrityError, match=field):
        load_reference_package_tables(package_dir)


def test_integrity_loader_rejects_manifest_row_count_mismatch(tmp_path: Path) -> None:
    package_dir = tmp_path / "reference-package"
    _write_published_package(package_dir, _valid_tables())
    manifest_path = package_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"]["players.csv"]["rowCount"] += 1
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(
        ReferencePackageIntegrityError,
        match=r"players\.csv rowCount mismatch",
    ):
        load_reference_package_tables(package_dir)


def test_package_rejects_header_order_mismatch(tmp_path: Path) -> None:
    package_dir = tmp_path / "reference-package"
    _write_package(package_dir, _valid_tables())
    players_path = package_dir / "players.csv"
    header = list(reversed(_headers()["players.csv"]))
    with players_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)

    with pytest.raises(ContractValidationError, match=r"players\.csv header mismatch"):
        validate_reference_package(package_dir)


def test_tables_reject_missing_required_value() -> None:
    tables = _valid_tables()
    tables["players.csv"][0]["displayName"] = ""

    with pytest.raises(
        ContractValidationError,
        match=r"players\.csv row 1 field displayName is required",
    ):
        validate_reference_tables(tables)


@pytest.mark.parametrize(
    ("file_name", "field", "value", "message"),
    [
        ("players.csv", "playerId", 101, "must be non-empty text"),
        ("players.csv", "draftYear", "2020.5", "must be an integer"),
        ("players.csv", "birthDate", "April 3", "must be an ISO 8601 date"),
        ("player_stats.csv", "points", math.inf, "must be a finite number"),
        ("player_attributes.csv", "insideScoring", 24, "must be at least 25"),
        ("player_attributes.csv", "overall", 100, "must be at most 99"),
        ("player_attributes.csv", "impactPercentile", 1.1, "must be at most 1"),
        ("player_attributes.csv", "talentTier", "bench", "must be one of"),
        ("sources.csv", "sha256", "not-a-hash", "must be a lowercase"),
        (
            "sources.csv",
            "processedAt",
            "2026-07-13T12:30:00",
            "must be an ISO 8601 datetime with a timezone",
        ),
    ],
)
def test_tables_reject_invalid_scalar_types(
    file_name: str, field: str, value: object, message: str
) -> None:
    tables = _valid_tables()
    tables[file_name][0][field] = value

    with pytest.raises(ContractValidationError, match=message):
        validate_reference_tables(tables)


def test_tables_reject_duplicate_unique_key() -> None:
    tables = _valid_tables()
    tables["players.csv"].append(copy.deepcopy(tables["players.csv"][0]))

    with pytest.raises(
        ContractValidationError,
        match=r"players\.csv violates unique key \(playerId\)",
    ):
        validate_reference_tables(tables)


def test_tables_reject_orphan_player_relationship() -> None:
    tables = _valid_tables()
    tables["player_stats.csv"][0]["playerId"] = "player_missing"

    with pytest.raises(
        ContractValidationError,
        match=r"relationship playerStatsReferencePlayers.*player_stats\.csv.*playerId",
    ):
        validate_reference_tables(tables)


def test_tables_reject_unregistered_source_type_relationship() -> None:
    tables = _valid_tables()
    tables["player_source_ids.csv"][0]["sourceType"] = "unknown_source"

    with pytest.raises(
        ContractValidationError,
        match=r"relationship playerSourceTypesReferenceSources.*sourceType",
    ):
        validate_reference_tables(tables)


def test_tables_require_one_attribute_row_per_statistics_row() -> None:
    tables = _valid_tables()
    tables["player_attributes.csv"].clear()

    with pytest.raises(
        ContractValidationError,
        match=r"relationship referencePlayerSeasonGrain key-set mismatch.*"
        r"player_attributes\.csv.*playerSeasonId, playerId, season",
    ):
        validate_reference_tables(tables)


def test_attribute_rows_enforce_unique_player_season_keys() -> None:
    tables = _valid_tables()
    tables["player_attributes.csv"].append(
        copy.deepcopy(tables["player_attributes.csv"][0])
    )

    with pytest.raises(
        ContractValidationError,
        match=r"player_attributes\.csv violates unique key \(playerSeasonId\)",
    ):
        validate_reference_tables(tables)


def test_attribute_rows_enforce_player_foreign_key() -> None:
    tables = _valid_tables()
    tables["player_attributes.csv"][0]["playerId"] = "player_missing"

    with pytest.raises(
        ContractValidationError,
        match="playerAttributesReferencePlayers",
    ):
        validate_reference_tables(tables)


def test_attribute_rows_require_formula_version() -> None:
    tables = _valid_tables()
    tables["player_attributes.csv"][0]["formulaVersion"] = ""

    with pytest.raises(
        ContractValidationError,
        match=r"player_attributes\.csv row 1 field formulaVersion is required",
    ):
        validate_reference_tables(tables)
