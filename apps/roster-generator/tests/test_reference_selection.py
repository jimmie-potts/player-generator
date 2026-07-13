from __future__ import annotations

import csv
import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pandas as pd
import pytest
import yaml
from player_attribute_engine import load_formula
from player_data_contracts import REFERENCE_CONTRACT_VERSION, load_reference_contract
from player_data_contracts.io import sha256_file
from player_data_contracts.package import content_hash
from roster_generator.cli import main
from roster_generator.publication import validate_published_roster_package
from roster_generator.reference_package import (
    LoadedReferencePackage,
    ReferencePackageError,
    load_reference_package,
)
from roster_generator.selection import (
    SelectionError,
    SelectionSettings,
    eligible_candidates,
    select_templates,
)


def _value(column: dict[str, Any]) -> object:
    return {
        "string": "value",
        "integer": 1,
        "number": 1.0,
        "date": "2000-01-01",
        "datetime": "2026-07-13T12:00:00Z",
        "sha256": "0" * 64,
    }[column["type"]]


def _row(file_contract: dict[str, Any], **overrides: object) -> dict[str, object]:
    return {
        column["name"]: overrides.get(column["name"], _value(column))
        for column in file_contract["columns"]
    }


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_manifest(package: Path, row_counts: dict[str, int]) -> None:
    contract = load_reference_contract()
    filenames = (*contract["files"], "audit.json")
    hashes = {filename: sha256_file(package / filename) for filename in filenames}
    manifest = {
        "manifestVersion": 1,
        "packageType": "reference",
        "packageVersion": 1,
        "createdAt": "2026-07-13T12:00:00Z",
        "contractVersions": {
            filename: REFERENCE_CONTRACT_VERSION for filename in contract["files"]
        },
        "inputs": [],
        "files": {
            filename: {"rowCount": row_counts[filename], "sha256": hashes[filename]}
            for filename in filenames
        },
        "contentHash": content_hash(hashes),
    }
    (package / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _refresh_hashes(package: Path) -> None:
    manifest_path = package / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    hashes = {filename: sha256_file(package / filename) for filename in manifest["files"]}
    for filename, digest in hashes.items():
        manifest["files"][filename]["sha256"] = digest
    manifest["contentHash"] = content_hash(hashes)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


@pytest.fixture
def reference_package(tmp_path: Path) -> Path:
    package = tmp_path / "reference-package"
    package.mkdir()
    contract = load_reference_contract()
    files = contract["files"]
    player_ids = ("ref-player-1", "ref-player-2", "ref-player-3")
    season_ids = ("ref-season-1", "ref-season-2", "ref-season-3")

    players = [
        _row(
            files["players.csv"],
            playerId=player_id,
            displayName=f"Reference Player {index}",
            firstName="Reference",
            lastName=f"Player {index}",
            heightInches=74.0 + index,
            weightPounds=190.0 + index,
        )
        for index, player_id in enumerate(player_ids, start=1)
    ]
    seasons = [
        _row(
            files["player_seasons.csv"],
            playerSeasonId=season_id,
            playerId=player_id,
            season=2024,
            teamId=f"reference-team-{index}",
            teamAbbreviation=f"R{index}",
            games=60 + index,
            minutes=1500.0 + index * 100,
        )
        for index, (season_id, player_id) in enumerate(
            zip(season_ids, player_ids, strict=True), start=1
        )
    ]
    stats = [
        _row(
            files["player_stats.csv"],
            playerSeasonId=season_id,
            playerId=player_id,
            season=2024,
            fieldGoalsMade=300.0 + index,
            fieldGoalsAttempted=700.0 + index,
            twoPointersMade=200.0 + index,
            twoPointersAttempted=400.0 + index,
            threePointersMade=100.0 + index,
            threePointersAttempted=300.0 + index,
            freeThrowsMade=150.0 + index,
            freeThrowsAttempted=180.0 + index,
            minutesPerGame=28.0 + index,
            assistsPer36=4.0 + index,
            turnoversPer100=2.0 + index,
            stealsPer100=1.0 + index,
            blocksPer100=0.5 + index,
            pointsPer100=20.0 + index,
            twoPointAttemptFrequency=0.5,
            threePointAttemptFrequency=0.4,
        )
        for index, (season_id, player_id) in enumerate(
            zip(season_ids, player_ids, strict=True), start=1
        )
    ]
    advanced = [
        _row(
            files["player_advanced_stats.csv"],
            playerSeasonId=season_id,
            playerId=player_id,
            season=2024,
            estimatedDefensiveRating=110.0 - index,
            estimatedNetRating=2.0 + index,
            assistPercentage=10.0 + index,
            assistTurnoverRatio=1.5 + index,
            assistRatio=12.0 + index,
            offensiveReboundPercentage=3.0 + index,
            defensiveReboundPercentage=10.0 + index,
            estimatedTurnoverPercentage=8.0 + index,
            trueShootingPercentage=0.5 + index / 100,
            usagePercentage=18.0 + index,
            playerImpactEstimate=8.0 + index,
            defensiveWinSharesPer36=0.05 + index / 100,
        )
        for index, (season_id, player_id) in enumerate(
            zip(season_ids, player_ids, strict=True), start=1
        )
    ]
    source_ids = [
        _row(
            files["player_source_ids.csv"],
            playerId=player_id,
            sourceType="synthetic",
            sourcePlayerId=f"upstream-{index}",
        )
        for index, player_id in enumerate(player_ids, start=1)
    ]
    sources = [
        _row(
            files["sources.csv"],
            sourceId="synthetic-source",
            sourceType="synthetic",
            originalFilename="synthetic.parquet",
            adapterVersion=1,
            rowCount=3,
            licenseStatus="test-only",
        )
    ]
    tables = {
        "players.csv": players,
        "player_seasons.csv": seasons,
        "player_stats.csv": stats,
        "player_advanced_stats.csv": advanced,
        "player_source_ids.csv": source_ids,
        "sources.csv": sources,
    }
    for filename, rows in tables.items():
        _write_csv(package / filename, rows)
    audit = {"unresolved": [], "duplicates": []}
    (package / "audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    row_counts = {filename: len(rows) for filename, rows in tables.items()}
    row_counts["audit.json"] = 0
    _write_manifest(package, row_counts)
    return package


def _settings(**overrides: object) -> SelectionSettings:
    values: dict[str, object] = {
        "seasons": [2024],
        "season_weights": {2024: 1.0},
        "minimum_games": 20,
        "minimum_minutes": 500.0,
        "roster_size": 2,
        "minutes_weight_exponent": 0.5,
        "with_replacement": False,
    }
    values.update(overrides)
    return SelectionSettings.from_mapping(values)


def test_load_reference_package_validates_and_joins_typed_rows(
    reference_package: Path,
) -> None:
    loaded = load_reference_package(reference_package, load_formula())

    assert loaded.path == reference_package.resolve()
    assert loaded.content_hash == loaded.manifest["contentHash"]
    assert len(loaded.frame) == 3
    assert pd.api.types.is_integer_dtype(loaded.frame["season"])
    assert pd.api.types.is_float_dtype(loaded.frame["minutes"])
    assert "playerImpactEstimate" in loaded.frame
    assert "sourcePlayerId" not in loaded.frame
    assert loaded.forbidden_player_ids == {
        "ref-player-1",
        "ref-player-2",
        "ref-player-3",
        "upstream-1",
        "upstream-2",
        "upstream-3",
    }
    assert loaded.forbidden_team_ids == {
        "reference-team-1",
        "reference-team-2",
        "reference-team-3",
    }
    assert "reference player 1" in loaded.forbidden_names


@pytest.mark.parametrize("missing", ["manifest.json", "player_stats.csv"])
def test_load_reference_package_rejects_missing_files(
    reference_package: Path, missing: str
) -> None:
    (reference_package / missing).unlink()

    with pytest.raises(ReferencePackageError, match=missing):
        load_reference_package(reference_package, load_formula())


def test_load_reference_package_rejects_file_hash_mismatch(reference_package: Path) -> None:
    with (reference_package / "players.csv").open("a", encoding="utf-8") as handle:
        handle.write("\n")

    with pytest.raises(ReferencePackageError, match=r"players\.csv SHA-256 mismatch"):
        load_reference_package(reference_package, load_formula())


def test_load_reference_package_rejects_content_hash_mismatch(reference_package: Path) -> None:
    manifest_path = reference_package / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["contentHash"] = "f" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ReferencePackageError, match="contentHash mismatch"):
        load_reference_package(reference_package, load_formula())


def test_load_reference_package_rejects_row_count_mismatch(reference_package: Path) -> None:
    manifest_path = reference_package / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"]["players.csv"]["rowCount"] += 1
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ReferencePackageError, match=r"players\.csv rowCount mismatch"):
        load_reference_package(reference_package, load_formula())


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("packageVersion", 2, "unsupported packageVersion 2"),
        ("contractVersions.players.csv", 2, "players.csv.*unsupported contract version 2"),
    ],
)
def test_load_reference_package_rejects_unsupported_package_contract_versions(
    reference_package: Path, field: str, value: int, message: str
) -> None:
    manifest_path = reference_package / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if field == "packageVersion":
        manifest[field] = value
    else:
        manifest["contractVersions"]["players.csv"] = value
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ReferencePackageError, match=message):
        load_reference_package(reference_package, load_formula())


def test_load_reference_package_rejects_incompatible_formula(reference_package: Path) -> None:
    formula = SimpleNamespace(reference_contract_version=2)

    with pytest.raises(ReferencePackageError, match="formula requires 2"):
        load_reference_package(reference_package, formula)


def test_load_reference_package_rejects_incompatible_formula_outputs(
    reference_package: Path,
) -> None:
    formula = replace(load_formula(), output_fields=("playerId",))

    with pytest.raises(ReferencePackageError, match="output_fields are incompatible"):
        load_reference_package(reference_package, formula)


def test_load_reference_package_names_orphan_relationship(reference_package: Path) -> None:
    path = reference_package / "player_seasons.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8", newline="")))
    rows[0]["playerId"] = "missing-player"
    _write_csv(path, rows)
    _refresh_hashes(reference_package)

    with pytest.raises(
        ReferencePackageError,
        match="relationship playerSeasonsReferencePlayers.*player_seasons.csv",
    ):
        load_reference_package(reference_package, load_formula())


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"season_weights": {}}, "cover exactly"),
        ({"season_weights": {2024: 0}}, "greater than 0"),
        ({"minimum_games": 1.5}, "minimum_games must be an integer"),
        ({"minimum_minutes": -1}, "minimum_minutes must be at least 0"),
        ({"minutes_weight_exponent": -0.5}, "minutes_weight_exponent must be at least 0"),
        ({"with_replacement": 1}, "with_replacement must be a boolean"),
    ],
)
def test_selection_settings_reject_invalid_values(
    override: dict[str, object], message: str
) -> None:
    with pytest.raises(SelectionError, match=message):
        _settings(**override)


def test_eligibility_evaluates_full_cohort_before_configured_filters(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    frame = pd.DataFrame(
        [
            {"playerId": "p1", "season": 2024, "games": 5, "minutes": 100.0},
            {"playerId": "p2", "season": 2024, "games": 40, "minutes": 900.0},
            {"playerId": "p3", "season": 2024, "games": 50, "minutes": 1000.0},
        ]
    )
    package = LoadedReferencePackage(
        path=tmp_path,
        manifest={},
        content_hash="0" * 64,
        frame=frame,
        forbidden_names=frozenset(),
        forbidden_player_ids=frozenset(),
        forbidden_team_ids=frozenset(),
    )
    seen_sizes: list[int] = []

    def evaluate(cohort: pd.DataFrame, formula: object) -> SimpleNamespace:
        seen_sizes.append(len(cohort))
        return SimpleNamespace(
            rows=[
                {"playerId": row.playerId, "rating": None if row.playerId == "p3" else 75}
                for row in cohort.itertuples()
            ]
        )

    monkeypatch.setattr("roster_generator.selection.evaluate_player_attributes", evaluate)
    monkeypatch.setattr(
        "roster_generator.selection.template_is_generation_viable", lambda _row: True
    )
    formula = SimpleNamespace(output_fields=("playerId", "rating"))

    candidates = eligible_candidates(package, formula, _settings(roster_size=1))

    assert seen_sizes == [3]
    assert candidates["playerId"].tolist() == ["p2"]


def test_empty_eligible_population_is_rejected(reference_package: Path) -> None:
    package = load_reference_package(reference_package, load_formula())

    with pytest.raises(SelectionError, match="No eligible reference templates"):
        eligible_candidates(
            package,
            load_formula(),
            _settings(minimum_minutes=100_000.0),
        )


def test_formula_complete_but_generation_inviable_templates_are_excluded(
    reference_package: Path,
) -> None:
    formula = load_formula()
    package = load_reference_package(reference_package, formula)
    excluded_id = str(package.frame.loc[0, "playerId"])
    for field in ("points", "assists", "turnovers", "steals", "blocks"):
        package.frame.loc[0, field] = None

    candidates = eligible_candidates(package, formula, _settings(roster_size=1))

    assert excluded_id not in set(candidates["playerId"].astype(str))
    assert len(candidates) == 2


def test_template_selection_is_deterministic(reference_package: Path) -> None:
    formula = load_formula()
    package = load_reference_package(reference_package, formula)
    settings = _settings()
    candidates = eligible_candidates(package, formula, settings)

    first = select_templates(candidates, settings, np.random.default_rng(412))
    second = select_templates(candidates, settings, np.random.default_rng(412))

    pd.testing.assert_frame_equal(first, second)
    assert len(first) == settings.roster_size
    assert first["playerId"].is_unique


def test_template_selection_rejects_insufficient_population() -> None:
    candidates = pd.DataFrame([{"playerId": "p1", "minutes": 500.0, "recencyWeight": 1.0}])

    with pytest.raises(SelectionError, match="too small"):
        select_templates(candidates, _settings(), np.random.default_rng(1))


def test_selection_settings_are_immutable() -> None:
    settings = _settings()

    with pytest.raises(TypeError):
        settings.season_weights[2024] = 2.0  # type: ignore[index]
    with pytest.raises(AttributeError):
        replace(settings, roster_size=3).roster_size = 4  # type: ignore[misc]


def test_cli_publishes_player_only_roster_package(
    reference_package: Path,
    roster_config: dict,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config = deepcopy(roster_config)
    output = tmp_path / "roster-v1"
    config["paths"]["reference_package_dir"] = str(reference_package)
    config["paths"]["roster_package_dir"] = str(output)
    config["selection"].update(
        {
            "seasons": [2024],
            "season_weights": {2024: 1.0},
            "roster_size": 3,
            "with_replacement": True,
        }
    )
    config_path = tmp_path / "roster.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    result = main(["--config", str(config_path), "generate"])

    assert result == 0
    assert f"Published normalized roster package to {output}." in capsys.readouterr().out
    manifest = validate_published_roster_package(output)
    assert manifest["files"]["players.csv"]["rowCount"] == 3
    assert {path.name for path in output.iterdir()} == {
        "players.csv",
        "player_stats.csv",
        "player_advanced_stats.csv",
        "player_attributes.csv",
        "manifest.json",
    }
