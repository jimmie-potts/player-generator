"""Integration tests for normalized roster-package publication."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pandas as pd
import pytest
from player_data_contracts import RATING_FIELDS
from roster_generator import publication
from roster_generator.generator import GeneratedRoster
from roster_generator.publication import (
    CSV_FILENAMES,
    RosterPublicationError,
    publish_roster_package,
    validate_published_roster_package,
)
from roster_generator.reference_package import LoadedReferencePackage

GOLDEN_PACKAGE_HASHES = {
    "manifest.json": "dd5e254162937a0eab9b3ab86dfed1e5bdc9599c530f6a942e3310c80d69daf0",
    "player_advanced_stats.csv": "f4e02d7c3c9b570c721f4cc2b07f11783fb4a12f1d8a707bcaff2d7291356c62",
    "player_attributes.csv": "c44f3fcb94326efb18922b4257194f4244681124cd38f890e7a7a3aa09265ec7",
    "player_stats.csv": "19923083d7e960f06ea69451526f5a7d4469b9e82847824aa8644e92dacb5191",
    "players.csv": "6b95438452cdc8834cd47e4afc67e86c6edfccfa2d3dd1deadcf9f95a09c26a3",
}


def _ratio(numerator: float, denominator: float, scale: float = 1.0) -> float:
    return round(numerator / denominator * scale, 8)


def _tables(display_name: str = "Generated Player") -> dict[str, list[dict[str, object]]]:
    player_id = "player_0123456789abcdef"
    games = 72
    minutes = 2160.0
    possessions = 5000.0
    two_made, two_attempted = 200, 400
    three_made, three_attempted = 100, 300
    free_made, free_attempted = 100, 120
    field_made = two_made + three_made
    field_attempted = two_attempted + three_attempted
    rebounds_offensive, rebounds_defensive = 50, 200
    rebounds = rebounds_offensive + rebounds_defensive
    assists, turnovers, steals, blocks = 300, 100, 50, 25
    points = 2 * two_made + 3 * three_made + free_made
    play_ending_denominator = field_attempted + 0.44 * free_attempted + assists + turnovers
    stats = {
        "playerId": player_id,
        "season": 2026,
        "games": games,
        "minutes": minutes,
        "possessions": possessions,
        "fieldGoalsMade": field_made,
        "fieldGoalsAttempted": field_attempted,
        "twoPointersMade": two_made,
        "twoPointersAttempted": two_attempted,
        "threePointersMade": three_made,
        "threePointersAttempted": three_attempted,
        "freeThrowsMade": free_made,
        "freeThrowsAttempted": free_attempted,
        "reboundsOffensive": rebounds_offensive,
        "reboundsDefensive": rebounds_defensive,
        "reboundsTotal": rebounds,
        "assists": assists,
        "turnovers": turnovers,
        "steals": steals,
        "blocks": blocks,
        "foulsPersonal": 150,
        "points": points,
        "plusMinusPoints": 20,
        "fieldGoalPercentage": _ratio(field_made, field_attempted),
        "twoPointPercentage": _ratio(two_made, two_attempted),
        "threePointPercentage": _ratio(three_made, three_attempted),
        "freeThrowPercentage": _ratio(free_made, free_attempted),
        "minutesPerGame": _ratio(minutes, games),
        "pointsPerGame": _ratio(points, games),
        "reboundsPerGame": _ratio(rebounds, games),
        "assistsPerGame": _ratio(assists, games),
        "turnoversPerGame": _ratio(turnovers, games),
        "threePointAttemptsPer36": _ratio(three_attempted, minutes, 36),
        "freeThrowAttemptsPer36": _ratio(free_attempted, minutes, 36),
        "offensiveReboundsPer36": _ratio(rebounds_offensive, minutes, 36),
        "defensiveReboundsPer36": _ratio(rebounds_defensive, minutes, 36),
        "assistsPer36": _ratio(assists, minutes, 36),
        "turnoversPer36": _ratio(turnovers, minutes, 36),
        "stealsPer36": _ratio(steals, minutes, 36),
        "blocksPer36": _ratio(blocks, minutes, 36),
        "pointsPer36": _ratio(points, minutes, 36),
        "plusMinusPer36": _ratio(20, minutes, 36),
        "pointsPer100": _ratio(points, possessions, 100),
        "assistsPer100": _ratio(assists, possessions, 100),
        "turnoversPer100": _ratio(turnovers, possessions, 100),
        "stealsPer100": _ratio(steals, possessions, 100),
        "blocksPer100": _ratio(blocks, possessions, 100),
        "twoPointAttemptFrequency": _ratio(two_attempted, field_attempted),
        "threePointAttemptFrequency": _ratio(three_attempted, field_attempted),
    }
    offense, defense = 112.0, 108.0
    estimated_offense, estimated_defense = 113.0, 109.5
    defensive_win_shares = 4.0
    advanced = {
        "playerId": player_id,
        "season": 2026,
        "estimatedOffensiveRating": estimated_offense,
        "offensiveRating": offense,
        "estimatedDefensiveRating": estimated_defense,
        "defensiveRating": defense,
        "estimatedNetRating": estimated_offense - estimated_defense,
        "netRating": offense - defense,
        "assistPercentage": 0.2,
        "assistTurnoverRatio": _ratio(assists, turnovers),
        "assistRatio": _ratio(assists, play_ending_denominator, 100),
        "offensiveReboundPercentage": 0.05,
        "defensiveReboundPercentage": 0.15,
        "reboundPercentage": 0.11,
        "estimatedTurnoverPercentage": _ratio(turnovers, play_ending_denominator, 100),
        "effectiveFieldGoalPercentage": _ratio(
            field_made + 0.5 * three_made, field_attempted
        ),
        "trueShootingPercentage": _ratio(
            points, 2 * (field_attempted + 0.44 * free_attempted)
        ),
        "usagePercentage": 0.2,
        "playerImpactEstimate": 0.1,
        "defensiveWinShares": defensive_win_shares,
        "defensiveWinSharesPer36": _ratio(defensive_win_shares, minutes, 36),
    }
    attributes: dict[str, object] = {"playerId": player_id}
    attributes.update({field: 75 for field in RATING_FIELDS})
    attributes.update(
        {
            "overall": 75,
            "impactPercentile": 0.5,
            "talentTier": "rotation",
            "formulaVersion": "1.0.0",
        }
    )
    return {
        "players.csv": [
            {
                "playerId": player_id,
                "displayName": display_name,
                "firstName": display_name.split()[0],
                "lastName": display_name.split()[-1],
                "age": 26,
                "heightInches": 78,
                "weightPounds": 215,
            }
        ],
        "player_stats.csv": [stats],
        "player_advanced_stats.csv": [advanced],
        "player_attributes.csv": [attributes],
    }


def _reference(tmp_path: Path) -> LoadedReferencePackage:
    return LoadedReferencePackage(
        path=tmp_path,
        manifest={},
        content_hash="a" * 64,
        frame=pd.DataFrame(),
        forbidden_names=frozenset({"reference player"}),
        forbidden_player_ids=frozenset(
            {"player_ffffffffffffffff", "player_eeeeeeeeeeeeeeee"}
        ),
        forbidden_team_ids=frozenset({"reference-team"}),
    )


def _generated(tables: dict[str, list[dict[str, object]]] | None = None) -> GeneratedRoster:
    return GeneratedRoster(
        tables=tables or _tables(),
        seed=41,
        configuration_hash="b" * 64,
    )


def test_publication_matches_golden_package_and_is_deterministic(tmp_path: Path) -> None:
    reference = _reference(tmp_path)
    first = publish_roster_package(
        _generated(),
        reference,
        tmp_path / "first",
        formula_version="1.0.0",
        formula_hash="c" * 64,
    )
    second = publish_roster_package(
        _generated(),
        reference,
        tmp_path / "second",
        formula_version="1.0.0",
        formula_hash="c" * 64,
    )

    assert {path.name for path in first.iterdir()} == {*CSV_FILENAMES, "manifest.json"}
    assert {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(first.iterdir())
    } == GOLDEN_PACKAGE_HASHES
    for filename in (*CSV_FILENAMES, "manifest.json"):
        assert (first / filename).read_bytes() == (second / filename).read_bytes()
    manifest = validate_published_roster_package(first)
    assert manifest["referencePackageHash"] == reference.content_hash
    assert manifest["formulaVersion"] == "1.0.0"
    assert manifest["formulaHash"] == "c" * 64
    assert manifest["seed"] == 41
    assert manifest["configurationHash"] == "b" * 64


def test_identity_leak_rejection_preserves_existing_package(tmp_path: Path) -> None:
    destination = tmp_path / "roster-v1"
    destination.mkdir()
    marker = destination / "old.txt"
    marker.write_text("keep", encoding="utf-8")

    with pytest.raises(RosterPublicationError, match="reuses a reference player name"):
        publish_roster_package(
            _generated(_tables("Reference Player")),
            _reference(tmp_path),
            destination,
            formula_version="1.0.0",
            formula_hash="c" * 64,
        )

    assert marker.read_text(encoding="utf-8") == "keep"
    assert list(destination.iterdir()) == [marker]


def test_reference_player_id_and_team_id_leaks_are_rejected(tmp_path: Path) -> None:
    id_tables = _tables()
    for rows in id_tables.values():
        rows[0]["playerId"] = "player_ffffffffffffffff"
    with pytest.raises(RosterPublicationError, match="reuses a reference player ID"):
        publish_roster_package(
            _generated(id_tables),
            _reference(tmp_path),
            tmp_path / "id-leak",
            formula_version="1.0.0",
            formula_hash="c" * 64,
        )

    source_id_tables = _tables()
    for rows in source_id_tables.values():
        rows[0]["playerId"] = "player_eeeeeeeeeeeeeeee"
    with pytest.raises(RosterPublicationError, match="reuses a reference player ID"):
        publish_roster_package(
            _generated(source_id_tables),
            _reference(tmp_path),
            tmp_path / "source-id-leak",
            formula_version="1.0.0",
            formula_hash="c" * 64,
        )

    team_tables = _tables()
    team_tables["players.csv"][0]["firstName"] = "reference-team"
    with pytest.raises(RosterPublicationError, match="reference team ID"):
        publish_roster_package(
            _generated(team_tables),
            _reference(tmp_path),
            tmp_path / "team-leak",
            formula_version="1.0.0",
            formula_hash="c" * 64,
        )


def test_contract_failure_never_publishes_partial_package(tmp_path: Path) -> None:
    tables = _tables()
    tables["player_stats.csv"][0]["points"] = 1
    destination = tmp_path / "roster-v1"

    with pytest.raises(ValueError, match="points.*semantic invariant"):
        publish_roster_package(
            _generated(tables),
            _reference(tmp_path),
            destination,
            formula_version="1.0.0",
            formula_hash="c" * 64,
        )

    assert not destination.exists()
    assert not list(tmp_path.glob(".roster-v1.tmp-*"))


def test_failed_final_replace_restores_previous_package(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "roster-v1"
    destination.mkdir()
    marker = destination / "old.txt"
    marker.write_text("keep", encoding="utf-8")
    real_replace = os.replace

    def fail_stage_replace(source: str | Path, target: str | Path) -> None:
        if Path(source).name.startswith(".roster-v1.tmp-") and Path(target) == destination:
            raise OSError("replace failed")
        real_replace(source, target)

    monkeypatch.setattr(publication.os, "replace", fail_stage_replace)

    with pytest.raises(OSError, match="replace failed"):
        publish_roster_package(
            _generated(),
            _reference(tmp_path),
            destination,
            formula_version="1.0.0",
            formula_hash="c" * 64,
        )

    assert marker.read_text(encoding="utf-8") == "keep"
    assert list(destination.iterdir()) == [marker]
    assert not list(tmp_path.glob(".roster-v1.backup-*"))


def test_manifest_validation_detects_tampered_csv(tmp_path: Path) -> None:
    destination = publish_roster_package(
        _generated(),
        _reference(tmp_path),
        tmp_path / "roster-v1",
        formula_version="1.0.0",
        formula_hash="c" * 64,
    )
    with (destination / "players.csv").open("a", encoding="utf-8") as handle:
        handle.write("\n")

    with pytest.raises(RosterPublicationError, match=r"players\.csv"):
        validate_published_roster_package(destination)

    manifest = json.loads((destination / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["contentHash"]


def test_manifest_validation_rejects_unmanifested_files(tmp_path: Path) -> None:
    destination = publish_roster_package(
        _generated(),
        _reference(tmp_path),
        tmp_path / "roster-v1",
        formula_version="1.0.0",
        formula_hash="c" * 64,
    )
    (destination / "source-to-roster-crosswalk.csv").write_text(
        "sourceId,playerId\n", encoding="utf-8"
    )

    with pytest.raises(RosterPublicationError, match="unexpected source-to-roster-crosswalk"):
        validate_published_roster_package(destination)


def test_formula_version_must_match_published_attributes(tmp_path: Path) -> None:
    with pytest.raises(RosterPublicationError, match="must all match"):
        publish_roster_package(
            _generated(),
            _reference(tmp_path),
            tmp_path / "roster-v1",
            formula_version="different-version",
            formula_hash="c" * 64,
        )

    destination = publish_roster_package(
        _generated(),
        _reference(tmp_path),
        tmp_path / "valid-roster-v1",
        formula_version="1.0.0",
        formula_hash="c" * 64,
    )
    manifest_path = destination / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["formulaVersion"] = "different-version"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    with pytest.raises(RosterPublicationError, match="must all match"):
        validate_published_roster_package(destination)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("manifestVersion", True, "manifestVersion must be an integer"),
        ("packageVersion", 1.0, "packageVersion must be an integer"),
        ("rowCount", True, "files.players.csv.rowCount must be an integer"),
    ],
)
def test_manifest_integer_fields_reject_boolean_and_float_aliases(
    tmp_path: Path,
    field: str,
    value: object,
    message: str,
) -> None:
    destination = publish_roster_package(
        _generated(),
        _reference(tmp_path),
        tmp_path / f"roster-{field}",
        formula_version="1.0.0",
        formula_hash="c" * 64,
    )
    manifest_path = destination / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if field == "rowCount":
        manifest["files"]["players.csv"][field] = value
    else:
        manifest[field] = value
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    with pytest.raises(RosterPublicationError, match=message):
        validate_published_roster_package(destination)
