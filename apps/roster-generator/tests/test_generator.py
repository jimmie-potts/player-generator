from __future__ import annotations

import hashlib
from copy import deepcopy
from pathlib import Path

import pandas as pd
import pytest
from player_attribute_engine import evaluate_player_attributes, formula_content_hash, load_formula
from player_data_contracts import validate_roster_tables
from roster_generator import generator as generator_module
from roster_generator.generator import RosterGenerationError, generate_roster_tables
from roster_generator.publication import publish_roster_package
from roster_generator.reference_package import LoadedReferencePackage

GOLDEN_GENERATED_PACKAGE_HASHES = {
    "manifest.json": "9c17c615dfc423582f1eab283d1964112502805155b0e5f05644863fd4a926e2",
    "player_advanced_stats.csv": "71640a5a53c275cf11d64f47ffc584dedc5afa9803ad000bfcb1a7a3f78144ae",
    "player_attributes.csv": "5de0e6605b0b11e390fa92526988efaadaade243e1c5ff1cee399c719529c6a6",
    "player_stats.csv": "dfcfdc1ab61ee16b896373d57e8e633339895bb40693103f2c0fe96a814f6b31",
    "players.csv": "691c899c1f66b6232ef41e80be8fc7eac0f0e6057f706b2f573619d41d54b8d1",
}


def _template(index: int) -> dict[str, object]:
    return {
        "playerId": f"reference-{index}",
        "displayName": f"Reference Player {index}",
        "firstName": "Reference",
        "lastName": f"Player {index}",
        "season": 2026,
        "age": 24 + index,
        "games": 72,
        "minutes": 2160.0 + index * 10,
        "heightInches": 74 + index,
        "weightPounds": 190 + index * 5,
        "fieldGoalsMade": 450 + index * 5,
        "fieldGoalsAttempted": 950 + index * 10,
        "twoPointersMade": 300 + index * 4,
        "twoPointersAttempted": 550 + index * 6,
        "threePointersMade": 150 + index,
        "threePointersAttempted": 400 + index * 4,
        "freeThrowsMade": 180 + index * 2,
        "freeThrowsAttempted": 220 + index * 2,
        "reboundsOffensive": 80 + index,
        "reboundsDefensive": 260 + index * 2,
        "assists": 300 + index * 4,
        "turnovers": 120 + index,
        "steals": 70 + index,
        "blocks": 35 + index,
        "foulsPersonal": 140 + index,
        "points": 1230 + index * 15,
        "plusMinusPoints": 90 + index,
        "minutesPerGame": 30.0,
        "threePointAttemptsPer36": 6.5 + index / 10,
        "freeThrowAttemptsPer36": 3.7 + index / 10,
        "offensiveReboundsPer36": 1.3 + index / 20,
        "defensiveReboundsPer36": 4.4 + index / 20,
        "assistsPer36": 5.0 + index / 10,
        "turnoversPer36": 2.0 + index / 20,
        "stealsPer36": 1.2 + index / 20,
        "blocksPer36": 0.6 + index / 20,
        "pointsPer36": 20.5 + index,
        "plusMinusPer36": 1.5 + index / 10,
        "pointsPer100": 28.0 + index,
        "assistsPer100": 7.0 + index / 10,
        "turnoversPer100": 3.0 + index / 10,
        "stealsPer100": 1.6 + index / 10,
        "blocksPer100": 0.8 + index / 10,
        "twoPointAttemptFrequency": 0.58,
        "threePointAttemptFrequency": 0.42,
        "estimatedOffensiveRating": 112.0 + index,
        "offensiveRating": 111.0 + index,
        "estimatedDefensiveRating": 110.0 - index / 2,
        "defensiveRating": 109.0 - index / 2,
        "estimatedNetRating": 2.0 + index,
        "netRating": 2.0 + index,
        "assistPercentage": 0.18 + index / 100,
        "assistTurnoverRatio": 2.3 + index / 10,
        "assistRatio": 18.0 + index,
        "offensiveReboundPercentage": 0.04 + index / 1000,
        "defensiveReboundPercentage": 0.14 + index / 1000,
        "reboundPercentage": 0.09 + index / 1000,
        "estimatedTurnoverPercentage": 9.0 + index / 10,
        "effectiveFieldGoalPercentage": 0.54 + index / 100,
        "trueShootingPercentage": 0.58 + index / 100,
        "usagePercentage": 0.20 + index / 100,
        "playerImpactEstimate": 0.10 + index / 100,
        "defensiveWinShares": 4.0 + index / 10,
        "defensiveWinSharesPer36": 0.07 + index / 100,
        "recencyWeight": 1.0,
    }


def _package(tmp_path: Path) -> LoadedReferencePackage:
    frame = pd.DataFrame([_template(index) for index in range(1, 5)])
    return LoadedReferencePackage(
        path=tmp_path,
        manifest={},
        content_hash="a" * 64,
        frame=frame,
        forbidden_names=frozenset(
            str(value).casefold() for value in frame["displayName"]
        ),
        forbidden_player_ids=frozenset(str(value) for value in frame["playerId"]),
        forbidden_team_ids=frozenset(),
    )


def _config(roster_config: dict, *, roster_size: int = 4) -> dict:
    config = deepcopy(roster_config)
    config["selection"]["seasons"] = [2026]
    config["selection"]["season_weights"] = {2026: 1.0}
    config["selection"]["roster_size"] = roster_size
    config["selection"]["with_replacement"] = False
    return config


@pytest.fixture(autouse=True)
def _deterministic_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        generator_module,
        "eligible_candidates",
        lambda package, _formula, _settings: package.frame,
    )
    monkeypatch.setattr(
        generator_module,
        "select_templates",
        lambda candidates, settings, _rng: candidates.iloc[: settings.roster_size]
        .copy()
        .reset_index(drop=True),
    )


def test_generation_is_deterministic_consistent_and_identity_safe(
    tmp_path: Path,
    roster_config: dict,
) -> None:
    package = _package(tmp_path)
    formula = load_formula()
    config = _config(roster_config)

    first = generate_roster_tables(package, formula, config, seed=42)
    second = generate_roster_tables(package, formula, config, seed=42)

    assert first == second
    validate_roster_tables(first.tables)
    players = first.tables["players.csv"]
    assert len(players) == 4
    assert len({row["playerId"] for row in players}) == 4
    assert not {str(row["playerId"]) for row in players} & package.forbidden_player_ids
    assert not {
        str(row["displayName"]).casefold() for row in players
    } & package.forbidden_names
    for stats, advanced in zip(
        first.tables["player_stats.csv"],
        first.tables["player_advanced_stats.csv"],
        strict=True,
    ):
        assert advanced["assistRatio"] != stats["assistsPer100"]
        assert advanced["estimatedTurnoverPercentage"] != stats["turnoversPer100"]

    output = publish_roster_package(
        first,
        package,
        tmp_path / "golden-roster-v1",
        formula_version=formula.formula_version,
        formula_hash=formula_content_hash(),
    )
    assert {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(output.iterdir())
    } == GOLDEN_GENERATED_PACKAGE_HASHES


def test_published_attributes_are_reproducible_through_shared_engine(
    tmp_path: Path,
    roster_config: dict,
) -> None:
    formula = load_formula()
    generated = generate_roster_tables(
        _package(tmp_path), formula, _config(roster_config), seed=77
    )
    frame = pd.DataFrame(generated.tables["player_stats.csv"]).merge(
        pd.DataFrame(generated.tables["player_advanced_stats.csv"]),
        on=["playerId", "season"],
        validate="one_to_one",
    )

    reevaluated = evaluate_player_attributes(frame, formula)

    assert generated.tables["player_attributes.csv"] == reevaluated.rows


def test_missing_raw_event_counts_are_inferred_from_published_rates(
    tmp_path: Path,
    roster_config: dict,
) -> None:
    package = _package(tmp_path)
    for field in ("assists", "turnovers", "steals", "blocks"):
        package.frame[field] = None

    generated = generate_roster_tables(
        package, load_formula(), _config(roster_config), seed=10
    )

    for row in generated.tables["player_stats.csv"]:
        assert all(row[field] is not None for field in ("assists", "turnovers", "steals", "blocks"))
    validate_roster_tables(generated.tables)


def test_zero_shooting_attempts_remain_valid_after_mutation(
    tmp_path: Path,
    roster_config: dict,
) -> None:
    package = _package(tmp_path)
    package.frame.loc[0, "threePointersMade"] = 0
    package.frame.loc[0, "threePointersAttempted"] = 0

    generated = generate_roster_tables(
        package, load_formula(), _config(roster_config), seed=10
    )

    stats = generated.tables["player_stats.csv"][0]
    assert stats["threePointersMade"] == 0
    assert stats["threePointersAttempted"] == 0
    assert stats["threePointPercentage"] is None
    validate_roster_tables(generated.tables)


def test_mutation_configuration_is_exact_and_nonnegative(
    tmp_path: Path,
    roster_config: dict,
) -> None:
    config = _config(roster_config)
    config["mutation"]["unknown"] = 1

    with pytest.raises(RosterGenerationError, match="unknown keys: unknown"):
        generate_roster_tables(_package(tmp_path), load_formula(), config)


def test_unsupported_configured_roster_contract_is_rejected_before_generation(
    tmp_path: Path,
    roster_config: dict,
) -> None:
    config = _config(roster_config)
    config["project"]["roster_contract_version"] = 2

    with pytest.raises(
        RosterGenerationError,
        match="Unsupported configured roster contract version 2",
    ):
        generate_roster_tables(_package(tmp_path), load_formula(), config)
