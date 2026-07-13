from __future__ import annotations

import copy
import csv
import json
from pathlib import Path

import player_data_contracts.roster as roster_module
import pytest
from player_data_contracts import (
    ROSTER_CONTRACT_VERSION,
    ContractValidationError,
    load_roster_contract,
    validate_roster_package,
    validate_roster_tables,
)

PLAYER_ID = "player_0123456789abcdef"


def _headers() -> dict[str, tuple[str, ...]]:
    contract = load_roster_contract()
    return {
        file_name: tuple(column["name"] for column in file_contract["columns"])
        for file_name, file_contract in contract["files"].items()
    }


def _row(file_name: str, **values: object) -> dict[str, object]:
    row = dict.fromkeys(_headers()[file_name], None)
    row.update(values)
    return row


def _valid_tables(*, rounded: bool = False) -> dict[str, list[dict[str, object]]]:
    def derived(value: float) -> float:
        return round(value, 8) if rounded else value

    ratings = {
        field: 70
        for field in _headers()["player_attributes.csv"]
        if field not in {"playerId", "impactPercentile", "talentTier", "formulaVersion"}
    }
    return {
        "players.csv": [
            _row(
                "players.csv",
                playerId=PLAYER_ID,
                displayName="Avery Rivers",
                firstName="Avery",
                lastName="Rivers",
                age=None,
                heightInches=78,
                weightPounds=None,
            )
        ],
        "player_stats.csv": [
            _row(
                "player_stats.csv",
                playerId=PLAYER_ID,
                season=2026,
                games=10,
                minutes=300,
                possessions=600,
                fieldGoalsMade=150,
                fieldGoalsAttempted=350,
                twoPointersMade=100,
                twoPointersAttempted=200,
                threePointersMade=50,
                threePointersAttempted=150,
                freeThrowsMade=80,
                freeThrowsAttempted=100,
                reboundsOffensive=30,
                reboundsDefensive=100,
                reboundsTotal=130,
                assists=120,
                turnovers=40,
                steals=20,
                blocks=10,
                foulsPersonal=25,
                points=430,
                plusMinusPoints=15,
                fieldGoalPercentage=derived(150 / 350),
                twoPointPercentage=0.5,
                threePointPercentage=derived(50 / 150),
                freeThrowPercentage=0.8,
                minutesPerGame=30,
                pointsPerGame=43,
                reboundsPerGame=13,
                assistsPerGame=12,
                turnoversPerGame=4,
                threePointAttemptsPer36=18,
                freeThrowAttemptsPer36=12,
                offensiveReboundsPer36=3.6,
                defensiveReboundsPer36=12,
                assistsPer36=14.4,
                turnoversPer36=4.8,
                stealsPer36=2.4,
                blocksPer36=1.2,
                pointsPer36=51.6,
                plusMinusPer36=1.8,
                pointsPer100=derived(430 / 600 * 100),
                assistsPer100=20,
                turnoversPer100=derived(40 / 600 * 100),
                stealsPer100=derived(20 / 600 * 100),
                blocksPer100=derived(10 / 600 * 100),
                twoPointAttemptFrequency=derived(200 / 350),
                threePointAttemptFrequency=derived(150 / 350),
            )
        ],
        "player_advanced_stats.csv": [
            _row(
                "player_advanced_stats.csv",
                playerId=PLAYER_ID,
                season=2026,
                estimatedOffensiveRating=116,
                offensiveRating=115,
                estimatedDefensiveRating=107,
                defensiveRating=108,
                estimatedNetRating=9,
                netRating=7,
                assistPercentage=0.25,
                assistTurnoverRatio=3,
                assistRatio=derived(120 / (350 + 0.44 * 100 + 120 + 40) * 100),
                offensiveReboundPercentage=0.1,
                defensiveReboundPercentage=0.2,
                reboundPercentage=0.14,
                estimatedTurnoverPercentage=derived(
                    40 / (350 + 0.44 * 100 + 120 + 40) * 100
                ),
                effectiveFieldGoalPercentage=0.5,
                trueShootingPercentage=derived(430 / (2 * (350 + 0.44 * 100))),
                usagePercentage=0.25,
                playerImpactEstimate=0.15,
                defensiveWinShares=2.5,
                defensiveWinSharesPer36=0.3,
            )
        ],
        "player_attributes.csv": [
            _row(
                "player_attributes.csv",
                playerId=PLAYER_ID,
                **ratings,
                impactPercentile=0.5,
                talentTier="starter",
                formulaVersion="1.0.0",
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


def test_roster_contract_has_exact_normalized_csv_headers() -> None:
    contract = load_roster_contract()

    assert contract["contractVersion"] == ROSTER_CONTRACT_VERSION == 1
    assert tuple(contract["files"]) == (
        "players.csv",
        "player_stats.csv",
        "player_advanced_stats.csv",
        "player_attributes.csv",
    )
    assert _headers()["players.csv"] == (
        "playerId",
        "displayName",
        "firstName",
        "lastName",
        "age",
        "heightInches",
        "weightPounds",
    )
    assert _headers()["player_stats.csv"] == (
        "playerId",
        "season",
        "games",
        "minutes",
        "possessions",
        "fieldGoalsMade",
        "fieldGoalsAttempted",
        "twoPointersMade",
        "twoPointersAttempted",
        "threePointersMade",
        "threePointersAttempted",
        "freeThrowsMade",
        "freeThrowsAttempted",
        "reboundsOffensive",
        "reboundsDefensive",
        "reboundsTotal",
        "assists",
        "turnovers",
        "steals",
        "blocks",
        "foulsPersonal",
        "points",
        "plusMinusPoints",
        "fieldGoalPercentage",
        "twoPointPercentage",
        "threePointPercentage",
        "freeThrowPercentage",
        "minutesPerGame",
        "pointsPerGame",
        "reboundsPerGame",
        "assistsPerGame",
        "turnoversPerGame",
        "threePointAttemptsPer36",
        "freeThrowAttemptsPer36",
        "offensiveReboundsPer36",
        "defensiveReboundsPer36",
        "assistsPer36",
        "turnoversPer36",
        "stealsPer36",
        "blocksPer36",
        "pointsPer36",
        "plusMinusPer36",
        "pointsPer100",
        "assistsPer100",
        "turnoversPer100",
        "stealsPer100",
        "blocksPer100",
        "twoPointAttemptFrequency",
        "threePointAttemptFrequency",
    )
    assert _headers()["player_advanced_stats.csv"] == (
        "playerId",
        "season",
        "estimatedOffensiveRating",
        "offensiveRating",
        "estimatedDefensiveRating",
        "defensiveRating",
        "estimatedNetRating",
        "netRating",
        "assistPercentage",
        "assistTurnoverRatio",
        "assistRatio",
        "offensiveReboundPercentage",
        "defensiveReboundPercentage",
        "reboundPercentage",
        "estimatedTurnoverPercentage",
        "effectiveFieldGoalPercentage",
        "trueShootingPercentage",
        "usagePercentage",
        "playerImpactEstimate",
        "defensiveWinShares",
        "defensiveWinSharesPer36",
    )
    assert _headers()["player_attributes.csv"] == (
        "playerId",
        "insideScoring",
        "threePointShooting",
        "freeThrowShooting",
        "scoringVolume",
        "playmaking",
        "ballSecurity",
        "offensiveRebounding",
        "defensiveRebounding",
        "perimeterDefense",
        "interiorDefense",
        "stamina",
        "durability",
        "overall",
        "impactPercentile",
        "talentTier",
        "formulaVersion",
    )


def test_valid_tables_and_csv_package_are_accepted(tmp_path: Path) -> None:
    tables = _valid_tables(rounded=True)
    validate_roster_tables(tables)

    package_dir = tmp_path / "roster-v1"
    _write_package(package_dir, tables)
    (package_dir / "manifest.json").write_text("{}\n", encoding="utf-8")
    validate_roster_package(package_dir)


def test_forward_contract_version_is_rejected() -> None:
    with pytest.raises(
        ContractValidationError,
        match="Unsupported roster contract version: 2",
    ):
        load_roster_contract(version=2)


def test_packaged_contract_version_drift_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    schema_dir = tmp_path / "schemas"
    schema_dir.mkdir()
    contract = load_roster_contract()
    contract["contractVersion"] = 2
    (schema_dir / "roster-v1.schema.json").write_text(json.dumps(contract), encoding="utf-8")
    monkeypatch.setattr(roster_module, "files", lambda package: tmp_path)

    with pytest.raises(
        ContractValidationError,
        match="does not declare version 1",
    ):
        roster_module.load_roster_contract()


@pytest.mark.parametrize(
    ("file_name", "field", "value", "message"),
    [
        ("players.csv", "playerId", "reference_123", "must match pattern"),
        ("players.csv", "age", 17, "must be at least 18"),
        ("players.csv", "heightInches", 97, "must be at most 96"),
        ("player_stats.csv", "points", 42.5, "must be an integer"),
        ("player_attributes.csv", "overall", 100, "must be at most 99"),
        ("player_attributes.csv", "impactPercentile", -0.1, "must be at least 0"),
        ("player_attributes.csv", "talentTier", "unknown", "must be one of"),
        (
            "player_advanced_stats.csv",
            "playerImpactEstimate",
            1.1,
            "must be at most 1",
        ),
        (
            "player_advanced_stats.csv",
            "effectiveFieldGoalPercentage",
            1.50000001,
            "must be at most 1.5",
        ),
        (
            "player_advanced_stats.csv",
            "trueShootingPercentage",
            1.50000001,
            "must be at most 1.5",
        ),
    ],
)
def test_scalar_patterns_ranges_and_enums_are_enforced(
    file_name: str, field: str, value: object, message: str
) -> None:
    tables = _valid_tables()
    tables[file_name][0][field] = value

    with pytest.raises(ContractValidationError, match=message):
        validate_roster_tables(tables)


def test_player_and_player_season_exact_key_sets_are_enforced() -> None:
    tables = _valid_tables()
    second_id = "player_fedcba9876543210"
    second_player = copy.deepcopy(tables["players.csv"][0])
    second_player["playerId"] = second_id
    tables["players.csv"].append(second_player)

    with pytest.raises(
        ContractValidationError,
        match=r"relationship rosterPlayerSet key-set mismatch",
    ):
        validate_roster_tables(tables)

    tables = _valid_tables()
    tables["player_advanced_stats.csv"][0]["season"] = 2025
    with pytest.raises(
        ContractValidationError,
        match=r"relationship rosterPlayerSeasonGrain key-set mismatch",
    ):
        validate_roster_tables(tables)


def test_every_roster_player_requires_stats_and_advanced_stats() -> None:
    tables = _valid_tables()
    tables["player_stats.csv"] = []
    tables["player_advanced_stats.csv"] = []

    with pytest.raises(
        ContractValidationError,
        match=r"relationship rosterPlayerSet key-set mismatch",
    ):
        validate_roster_tables(tables)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("minutes", 0, "must be greater than zero"),
        ("possessions", 0, "must be greater than zero"),
        ("twoPointersMade", 201, "cannot exceed twoPointersAttempted"),
        ("fieldGoalsMade", 149, r"twoPointersMade \+ threePointersMade"),
        ("fieldGoalsAttempted", 349, r"twoPointersAttempted \+ threePointersAttempted"),
        ("points", 429, r"2 \* twoPointersMade"),
        ("reboundsTotal", 129, r"reboundsOffensive \+ reboundsDefensive"),
        ("fieldGoalPercentage", 0.4, "fieldGoalsMade / fieldGoalsAttempted"),
        ("pointsPerGame", 42, "points / games"),
        ("assistsPer36", 14, r"assists / minutes \* 36"),
        ("pointsPer100", 70, r"points / possessions \* 100"),
    ],
)
def test_traditional_stat_invariants_are_enforced(field: str, value: object, message: str) -> None:
    tables = _valid_tables()
    tables["player_stats.csv"][0][field] = value

    with pytest.raises(ContractValidationError, match=message):
        validate_roster_tables(tables)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("estimatedNetRating", 8, "estimatedOffensiveRating - estimatedDefensiveRating"),
        ("netRating", 6, "offensiveRating - defensiveRating"),
        ("effectiveFieldGoalPercentage", 0.4, r"fieldGoalsMade \+ 0.5"),
        ("trueShootingPercentage", 0.5, r"fieldGoalsAttempted \+ 0.44"),
        ("assistTurnoverRatio", 2, r"assists / max\(turnovers, 1\)"),
        ("assistRatio", 19, r"fieldGoalsAttempted \+ 0.44"),
        ("estimatedTurnoverPercentage", 5, r"fieldGoalsAttempted \+ 0.44"),
        ("defensiveWinSharesPer36", 0.2, r"defensiveWinShares / minutes \* 36"),
    ],
)
def test_advanced_stat_invariants_are_enforced(field: str, value: object, message: str) -> None:
    tables = _valid_tables()
    tables["player_advanced_stats.csv"][0][field] = value

    with pytest.raises(ContractValidationError, match=message):
        validate_roster_tables(tables)


def test_shooting_efficiencies_above_one_are_valid_through_one_point_five() -> None:
    tables = _valid_tables()
    stats = tables["player_stats.csv"][0]
    stats.update(
        {
            "fieldGoalsMade": 100,
            "fieldGoalsAttempted": 100,
            "twoPointersMade": 0,
            "twoPointersAttempted": 0,
            "threePointersMade": 100,
            "threePointersAttempted": 100,
            "freeThrowsMade": 0,
            "freeThrowsAttempted": 0,
            "points": 300,
            "fieldGoalPercentage": 1,
            "twoPointPercentage": None,
            "threePointPercentage": 1,
            "freeThrowPercentage": None,
            "pointsPerGame": 30,
            "threePointAttemptsPer36": 12,
            "freeThrowAttemptsPer36": 0,
            "pointsPer36": 36,
            "pointsPer100": 50,
            "twoPointAttemptFrequency": 0,
            "threePointAttemptFrequency": 1,
        }
    )
    advanced = tables["player_advanced_stats.csv"][0]
    play_ending_denominator = 100 + 120 + 40
    advanced.update(
        {
            "assistRatio": 120 / play_ending_denominator * 100,
            "estimatedTurnoverPercentage": 40 / play_ending_denominator * 100,
            "effectiveFieldGoalPercentage": 1.5,
            "trueShootingPercentage": 1.5,
        }
    )

    validate_roster_tables(tables)


def test_zero_turnovers_require_finite_assist_turnover_ratio() -> None:
    tables = _valid_tables()
    stats = tables["player_stats.csv"][0]
    stats.update(
        {
            "turnovers": 0,
            "turnoversPerGame": 0,
            "turnoversPer36": 0,
            "turnoversPer100": 0,
        }
    )
    advanced = tables["player_advanced_stats.csv"][0]
    play_ending_denominator = 350 + 0.44 * 100 + 120
    advanced.update(
        {
            "assistTurnoverRatio": 120,
            "assistRatio": 120 / play_ending_denominator * 100,
            "estimatedTurnoverPercentage": 0,
        }
    )

    validate_roster_tables(tables)

    advanced["assistTurnoverRatio"] = 0
    with pytest.raises(
        ContractValidationError,
        match=r"assists / max\(turnovers, 1\)",
    ):
        validate_roster_tables(tables)


def test_zero_denominators_require_empty_derived_values() -> None:
    tables = _valid_tables()
    stats = tables["player_stats.csv"][0]
    for field in (
        "fieldGoalsMade",
        "fieldGoalsAttempted",
        "twoPointersMade",
        "twoPointersAttempted",
        "threePointersMade",
        "threePointersAttempted",
        "freeThrowsMade",
        "freeThrowsAttempted",
        "points",
    ):
        stats[field] = 0
    for field in (
        "fieldGoalPercentage",
        "twoPointPercentage",
        "threePointPercentage",
        "freeThrowPercentage",
        "twoPointAttemptFrequency",
        "threePointAttemptFrequency",
    ):
        stats[field] = None
    stats["pointsPerGame"] = 0
    stats["threePointAttemptsPer36"] = 0
    stats["freeThrowAttemptsPer36"] = 0
    stats["pointsPer36"] = 0
    stats["pointsPer100"] = 0
    advanced = tables["player_advanced_stats.csv"][0]
    advanced["effectiveFieldGoalPercentage"] = None
    advanced["trueShootingPercentage"] = None
    advanced["assistRatio"] = 75
    advanced["estimatedTurnoverPercentage"] = 25

    validate_roster_tables(tables)

    stats["fieldGoalPercentage"] = 0
    with pytest.raises(ContractValidationError, match="must be empty"):
        validate_roster_tables(tables)


def test_available_denominator_requires_derived_value() -> None:
    tables = _valid_tables()
    tables["player_stats.csv"][0]["pointsPer100"] = None

    with pytest.raises(ContractValidationError, match="is required when points / possessions"):
        validate_roster_tables(tables)


def test_nullable_source_counts_and_their_rates_are_accepted() -> None:
    tables = _valid_tables()
    stats = tables["player_stats.csv"][0]
    for field in (
        "reboundsOffensive",
        "reboundsDefensive",
        "reboundsTotal",
        "foulsPersonal",
        "plusMinusPoints",
        "reboundsPerGame",
        "offensiveReboundsPer36",
        "defensiveReboundsPer36",
        "plusMinusPer36",
    ):
        stats[field] = None

    validate_roster_tables(tables)


def test_unavailable_advanced_operands_require_empty_result() -> None:
    tables = _valid_tables()
    advanced = tables["player_advanced_stats.csv"][0]
    advanced["estimatedOffensiveRating"] = None
    advanced["estimatedNetRating"] = None
    advanced["offensiveReboundPercentage"] = None
    advanced["defensiveWinShares"] = None
    advanced["defensiveWinSharesPer36"] = None

    validate_roster_tables(tables)

    advanced["defensiveWinShares"] = -0.5
    advanced["defensiveWinSharesPer36"] = -0.06
    validate_roster_tables(tables)


def test_package_rejects_missing_csv_and_header_order(tmp_path: Path) -> None:
    package_dir = tmp_path / "roster-v1"
    _write_package(package_dir, _valid_tables())
    (package_dir / "player_attributes.csv").unlink()

    with pytest.raises(ContractValidationError, match="missing required table"):
        validate_roster_package(package_dir)

    _write_package(tmp_path / "other-roster", _valid_tables())
    players_path = tmp_path / "other-roster" / "players.csv"
    players_path.write_text("lastName,playerId\n", encoding="utf-8")
    with pytest.raises(ContractValidationError, match="header mismatch"):
        validate_roster_package(tmp_path / "other-roster")
