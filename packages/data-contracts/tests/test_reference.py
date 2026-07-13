from __future__ import annotations

import copy
import csv
import math
from pathlib import Path

import pytest
from player_data_contracts import (
    RATING_FIELDS,
    REFERENCE_CONTRACT_VERSION,
    SUPPORTED_REFERENCE_CONTRACT_VERSIONS,
    ContractValidationError,
    load_reference_contract,
    validate_reference_package,
    validate_reference_tables,
)
from reference_data_app.adapters import NBA_ADVANCED_STAT_MAP, NBA_TRADITIONAL_STAT_MAP


def _headers(
    version: int = REFERENCE_CONTRACT_VERSION,
) -> dict[str, tuple[str, ...]]:
    contract = load_reference_contract(version)
    return {
        file_name: tuple(column["name"] for column in file_contract["columns"])
        for file_name, file_contract in contract["files"].items()
    }


def _row(
    file_name: str,
    *,
    version: int = REFERENCE_CONTRACT_VERSION,
    **values: object,
) -> dict[str, object]:
    row = dict.fromkeys(_headers(version)[file_name], None)
    row.update(values)
    return row


def _valid_tables(
    version: int = REFERENCE_CONTRACT_VERSION,
) -> dict[str, list[dict[str, object]]]:
    player_id = "player_unicode"
    player_season_id = "playerSeason_unicode_2026"
    tables = {
        "players.csv": [
            _row(
                "players.csv",
                version=version,
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
                version=version,
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
                version=version,
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
                version=version,
                playerSeasonId=player_season_id,
                playerId=player_id,
                season=2026,
                usagePercentage=0.287,
                playerImpactEstimate=None,
            )
        ],
    }
    if version == 2:
        tables["player_attributes.csv"] = [
            _row(
                "player_attributes.csv",
                version=version,
                playerSeasonId=player_season_id,
                playerId=player_id,
                season=2026,
                insideScoring=75,
                overall=78,
                impactPercentile=0.8,
                talentTier="starter",
                formulaVersion="1.0.0",
            )
        ]
    tables.update(
        {
            "player_source_ids.csv": [
                _row(
                    "player_source_ids.csv",
                    version=version,
                    playerId=player_id,
                    sourceType="nba_playerstats",
                    sourcePlayerId="101",
                )
            ],
            "sources.csv": [
                _row(
                    "sources.csv",
                    version=version,
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
    )
    return tables


def _write_package(
    path: Path,
    tables: dict[str, list[dict[str, object]]],
    *,
    version: int = REFERENCE_CONTRACT_VERSION,
) -> None:
    path.mkdir()
    for file_name, rows in tables.items():
        header = _headers(version)[file_name]
        with (path / file_name).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=header, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)


def test_reference_v1_contract_resource_has_adapter_metric_order() -> None:
    contract = load_reference_contract(1)

    assert contract["contractVersion"] == 1
    assert tuple(contract["files"]) == (
        "players.csv",
        "player_seasons.csv",
        "player_stats.csv",
        "player_advanced_stats.csv",
        "player_source_ids.csv",
        "sources.csv",
    )
    headers = _headers(1)
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


def test_reference_v2_is_active_and_extends_v1_with_formula_outputs() -> None:
    v1 = load_reference_contract(1)
    v2 = load_reference_contract()

    assert REFERENCE_CONTRACT_VERSION == 2
    assert SUPPORTED_REFERENCE_CONTRACT_VERSIONS == (1, 2)
    assert v2["contractVersion"] == 2
    assert tuple(v2["files"]) == (
        "players.csv",
        "player_seasons.csv",
        "player_stats.csv",
        "player_advanced_stats.csv",
        "player_attributes.csv",
        "player_source_ids.csv",
        "sources.csv",
    )
    for file_name, file_contract in v1["files"].items():
        assert v2["files"][file_name] == file_contract

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
    attributes = v2["files"]["player_attributes.csv"]
    assert attributes["uniqueKeys"] == [["playerSeasonId"], ["playerId", "season"]]
    columns = {column["name"]: column for column in attributes["columns"]}
    for field in (*RATING_FIELDS, "overall"):
        assert columns[field] == {
            "name": field,
            "type": "integer",
            "required": False,
            "nullable": True,
            "minimum": 25,
            "maximum": 99,
        }
    assert columns["impactPercentile"]["minimum"] == 0
    assert columns["impactPercentile"]["maximum"] == 1
    assert columns["impactPercentile"]["nullable"] is True
    assert columns["talentTier"]["enum"] == [
        "superstar",
        "all_star",
        "starter",
        "rotation",
        "fringe",
    ]
    assert columns["talentTier"]["nullable"] is True
    assert columns["formulaVersion"]["required"] is True
    assert columns["formulaVersion"]["nullable"] is False
    relationship_names = {relationship["name"] for relationship in v2["relationships"]}
    assert {
        "playerAttributesReferencePlayers",
        "playerAttributesReferencePlayerSeasons",
    } <= relationship_names
    exact = next(
        relationship
        for relationship in v2["relationships"]
        if relationship["name"] == "aggregatePlayerSeasonGrain"
    )
    assert exact["files"] == [
        "player_seasons.csv",
        "player_stats.csv",
        "player_advanced_stats.csv",
        "player_attributes.csv",
    ]


def test_supplied_v1_contract_validates_with_v2_active(tmp_path: Path) -> None:
    contract = load_reference_contract(1)
    tables = _valid_tables(1)

    validate_reference_tables(tables, contract=contract)
    package_dir = tmp_path / "reference-v1"
    _write_package(package_dir, tables, version=1)
    validate_reference_package(package_dir, contract=contract)


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


def test_v2_tables_require_one_attribute_row_per_player_season() -> None:
    tables = _valid_tables()
    tables["player_attributes.csv"].clear()

    with pytest.raises(
        ContractValidationError,
        match=r"relationship aggregatePlayerSeasonGrain key-set mismatch.*"
        r"player_attributes\.csv.*playerSeasonId, playerId, season",
    ):
        validate_reference_tables(tables)


def test_v2_attribute_rows_enforce_unique_player_season_keys() -> None:
    tables = _valid_tables()
    tables["player_attributes.csv"].append(
        copy.deepcopy(tables["player_attributes.csv"][0])
    )

    with pytest.raises(
        ContractValidationError,
        match=r"player_attributes\.csv violates unique key \(playerSeasonId\)",
    ):
        validate_reference_tables(tables)


@pytest.mark.parametrize(
    ("field", "value", "relationship"),
    [
        ("playerId", "player_missing", "playerAttributesReferencePlayers"),
        (
            "playerSeasonId",
            "playerSeason_missing",
            "playerAttributesReferencePlayerSeasons",
        ),
    ],
)
def test_v2_attribute_rows_enforce_foreign_keys(
    field: str, value: str, relationship: str
) -> None:
    tables = _valid_tables()
    tables["player_attributes.csv"][0][field] = value

    with pytest.raises(ContractValidationError, match=relationship):
        validate_reference_tables(tables)


def test_v2_attribute_rows_require_formula_version() -> None:
    tables = _valid_tables()
    tables["player_attributes.csv"][0]["formulaVersion"] = ""

    with pytest.raises(
        ContractValidationError,
        match=r"player_attributes\.csv row 1 field formulaVersion is required",
    ):
        validate_reference_tables(tables)
