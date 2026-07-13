from __future__ import annotations

import copy
import csv
import math
from pathlib import Path

import pytest
from player_data_contracts import (
    REFERENCE_CONTRACT_VERSION,
    ContractValidationError,
    load_reference_contract,
    validate_reference_package,
    validate_reference_tables,
)
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
        "player_seasons.csv": [
            _row(
                "player_seasons.csv",
                playerSeasonId=player_season_id,
                playerId=player_id,
                season=2026,
                games=72,
                starts=None,
                wins=48,
                losses=24,
                minutes=2160.5,
            )
        ],
        "player_stats.csv": [
            _row(
                "player_stats.csv",
                playerSeasonId=player_season_id,
                playerId=player_id,
                season=2026,
                points=1350,
                twoPointPercentage=0.583,
            )
        ],
        "player_advanced_stats.csv": [
            _row(
                "player_advanced_stats.csv",
                playerSeasonId=player_season_id,
                playerId=player_id,
                season=2026,
                usagePercentage=0.287,
                playerImpactEstimate=None,
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
        header = _headers()[file_name]
        with (path / file_name).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=header, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)


def test_reference_v1_contract_resource_has_adapter_metric_order() -> None:
    contract = load_reference_contract()

    assert contract["contractVersion"] == REFERENCE_CONTRACT_VERSION == 1
    assert tuple(contract["files"]) == (
        "players.csv",
        "player_seasons.csv",
        "player_stats.csv",
        "player_advanced_stats.csv",
        "player_source_ids.csv",
        "sources.csv",
    )
    headers = _headers()
    assert headers["player_stats.csv"][3:] == tuple(NBA_TRADITIONAL_STAT_MAP.values())
    assert headers["player_advanced_stats.csv"][3:] == tuple(NBA_ADVANCED_STAT_MAP.values())
    assert headers["sources.csv"] == (
        "sourceId",
        "sourceType",
        "originalFilename",
        "sha256",
        "adapterVersion",
        "upstreamVersion",
        "rowCount",
        "processedAt",
        "licenseStatus",
    )


def test_valid_unicode_rows_and_optional_empty_values_are_accepted(tmp_path: Path) -> None:
    tables = _valid_tables()
    validate_reference_tables(tables)

    package_dir = tmp_path / "reference-package"
    _write_package(package_dir, tables)
    validate_reference_package(package_dir)


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
    tables["player_seasons.csv"][0]["playerId"] = "player_missing"

    with pytest.raises(
        ContractValidationError,
        match=r"relationship playerSeasonsReferencePlayers.*player_seasons\.csv.*playerId",
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


def test_tables_reject_player_season_key_set_mismatch() -> None:
    tables = _valid_tables()
    tables["player_advanced_stats.csv"].clear()

    with pytest.raises(
        ContractValidationError,
        match=r"relationship aggregatePlayerSeasonGrain key-set mismatch.*"
        r"player_advanced_stats\.csv.*playerSeasonId, playerId, season",
    ):
        validate_reference_tables(tables)
