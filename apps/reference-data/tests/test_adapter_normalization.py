from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from reference_data_app.adapters import (
    NBA_PLAYERSTATS_V1_REQUIRED_COLUMNS,
    AdapterValidationError,
    NormalizedSourceRow,
    normalize_source,
)


def _write_parquet(path: Path, rows: list[dict[str, object]]) -> Path:
    pd.DataFrame(rows).to_parquet(path, index=False)
    return path


def _nba_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        column: 0 for column in NBA_PLAYERSTATS_V1_REQUIRED_COLUMNS
    }
    row.update(
        {
            "player_id": 101,
            "player_name": "Sample Player",
            "team_id": 1610612737,
            "team_abbreviation": "ATL",
            "team_count": 1,
            "year": 2026,
            "age": 26.0,
            "gp": 72,
            "w": 45,
            "l": 27,
            "min": 2160.5,
            "player_height_inches": 78.0,
            "player_weight": "212",
            "country": "United States",
            "college": "Example College",
            "draft_year": "2021",
            "draft_round": "1",
            "draft_number": "15",
            "fgm": 500,
            "fga": 1000,
            "fg3m": 150,
            "fg3a": 400,
            "ftm": 200,
            "fta": 250,
            "pts": 1350,
            "fg2m": 350,
            "fg2a": 600,
            "fg2_pct": 0.583,
            "min_pergame": 30.007,
            "pts_per36": 22.495,
            "pts_per100possessions": 31.25,
            "fg2a_frequency": 0.6,
            "fg3a_frequency": 0.4,
            "off_rating": 121.4,
            "def_rating": 108.6,
            "usg_pct": 0.287,
            "ts_pct": 0.621,
            "pie": 0.167,
            "def_ws": 3.8,
            "def_ws_per36": 0.063,
        }
    )
    row.update(overrides)
    return row


def test_nba_and_espn_equivalent_bio_values_normalize_identically(tmp_path: Path) -> None:
    nba_path = _write_parquet(tmp_path / "nba.parquet", [_nba_row()])
    espn_path = _write_parquet(
        tmp_path / "espn.parquet",
        [
            {
                "id": "espn-101",
                "displayName": "Sample Player",
                "heightInches": 78,
                "weightPounds": 212.0,
                "country": "United States",
                "college": "Example College",
                "draftYear": 2021.0,
                "draftRound": 1,
                "draftNumber": "15",
            }
        ],
    )

    nba = normalize_source(nba_path, "nba-source", "nba_playerstats", 1)[0]
    espn = normalize_source(espn_path, "espn-source", "espn_player_details", 1)[0]

    assert isinstance(nba, NormalizedSourceRow)
    assert nba.source_id == "nba-source"
    assert nba.source_player_id == "101"
    assert espn.source_player_id == "espn-101"
    assert nba.display_name == espn.display_name == "Sample Player"
    shared_fields = {
        "heightInches",
        "weightPounds",
        "country",
        "college",
        "draftYear",
        "draftRound",
        "draftNumber",
    }
    assert {field: nba.player_fields[field] for field in shared_fields} == {
        field: espn.player_fields[field] for field in shared_fields
    }
    assert "firstName" not in espn.player_fields
    assert "lastName" not in espn.player_fields


def test_nba_stats_preserve_source_units_without_formula_derivations(tmp_path: Path) -> None:
    source_path = _write_parquet(tmp_path / "nba.parquet", [_nba_row()])

    player = normalize_source(source_path, "nba-source", "nba_playerstats", 1)[0]

    assert player.season_fields == {
        "season": 2026,
        "teamId": player.season_fields["teamId"],
        "teamAbbreviation": "ATL",
        "age": 26,
        "games": 72,
        "starts": None,
        "wins": 45,
        "losses": 27,
        "minutes": 2160.5,
    }
    assert str(player.season_fields["teamId"]).startswith("team_")
    assert player.season_fields["teamId"] != "1610612737"
    assert player.traditional_stats["points"] == 1350
    assert player.traditional_stats["twoPointPercentage"] == pytest.approx(0.583)
    assert player.traditional_stats["pointsPer36"] == pytest.approx(22.495)
    assert player.traditional_stats["pointsPer100"] == pytest.approx(31.25)
    assert player.traditional_stats["twoPointAttemptFrequency"] == pytest.approx(0.6)
    assert player.advanced_stats["offensiveRating"] == pytest.approx(121.4)
    assert player.advanced_stats["usagePercentage"] == pytest.approx(0.287)
    assert player.advanced_stats["trueShootingPercentage"] == pytest.approx(0.621)
    assert player.advanced_stats["playerImpactEstimate"] == pytest.approx(0.167)
    assert player.advanced_stats["defensiveWinShares"] == pytest.approx(3.8)
    assert "freeThrowRate" not in player.traditional_stats
    assert "adjustedTwoPointPercentage" not in player.traditional_stats


def test_nba_team_identity_requires_explicit_single_team_aggregate(tmp_path: Path) -> None:
    source_path = _write_parquet(
        tmp_path / "nba.parquet",
        [
            _nba_row(player_id=1, player_name="Single", team_count=1),
            _nba_row(
                player_id=2,
                player_name="Multiple",
                team_count=2,
                team_abbreviation="TOT",
            ),
            _nba_row(
                player_id=3,
                player_name="Unknown",
                team_count=None,
                team_id=None,
                team_abbreviation="UNK",
            ),
        ],
    )

    players = {
        row.source_player_id: row
        for row in normalize_source(source_path, "nba-source", "nba_playerstats", 1)
    }

    assert players["1"].season_fields["teamId"] is not None
    assert players["1"].season_fields["teamAbbreviation"] == "ATL"
    assert players["2"].season_fields["teamId"] is None
    assert players["2"].season_fields["teamAbbreviation"] is None
    assert players["3"].season_fields["teamId"] is None
    assert players["3"].season_fields["teamAbbreviation"] is None
    assert players["2"].source_context == {
        "sourceTeamId": 1610612737,
        "sourceTeamAbbreviation": "TOT",
        "teamCount": 2,
    }
    assert players["3"].source_context == {
        "sourceTeamId": None,
        "sourceTeamAbbreviation": "UNK",
        "teamCount": None,
    }


def test_optional_nulls_and_espn_aliases_are_conservative(tmp_path: Path) -> None:
    nba_path = _write_parquet(
        tmp_path / "nba.parquet",
        [
            _nba_row(
                player_weight=None,
                country=None,
                college="   ",
                draft_year="Undrafted",
                draft_round=None,
                draft_number="Undrafted",
                pie=None,
            )
        ],
    )
    espn_path = _write_parquet(
        tmp_path / "espn.parquet",
        [
            {
                "id": "espn-1",
                "displayName": "Alias Player",
                "firstName": None,
                "dateOfBirth": "2000-01-02",
                "heightInches": None,
                "height": 1.98,
                "weight": 96,
            }
        ],
    )

    nba = normalize_source(nba_path, "nba-source", "nba_playerstats", 1)[0]
    espn = normalize_source(espn_path, "espn-source", "espn_player_details", 1)[0]

    assert nba.player_fields["weightPounds"] is None
    assert nba.player_fields["country"] is None
    assert nba.player_fields["college"] is None
    assert nba.player_fields["draftYear"] is None
    assert nba.player_fields["draftNumber"] is None
    assert nba.advanced_stats["playerImpactEstimate"] is None
    assert espn.player_fields == {
        "firstName": None,
        "birthDate": "2000-01-02",
        "heightInches": None,
    }
    assert espn.season_fields is None
    assert espn.traditional_stats is None
    assert espn.advanced_stats is None
    assert espn.source_context == {}


def test_duplicate_source_player_season_keys_are_rejected(tmp_path: Path) -> None:
    source_path = _write_parquet(
        tmp_path / "duplicate.parquet",
        [
            _nba_row(player_id=101, year=2026),
            _nba_row(player_id=101, year=2026, player_name="Duplicate"),
        ],
    )

    with pytest.raises(AdapterValidationError) as error:
        normalize_source(source_path, "nba-source", "nba_playerstats", 1)

    message = str(error.value)
    assert str(source_path) in message
    assert "adapter nba_playerstats v1" in message
    assert "duplicate source player-season key ('101', 2026)" in message


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("player_id", "not-an-id"),
        ("year", "not-a-season"),
        ("gp", "many"),
        ("team_count", "multiple"),
        ("usg_pct", "high"),
    ],
)
def test_invalid_required_nba_ids_season_and_numeric_types_are_rejected(
    tmp_path: Path,
    field: str,
    value: object,
) -> None:
    source_path = _write_parquet(
        tmp_path / f"invalid-{field}.parquet",
        [_nba_row(**{field: value})],
    )

    with pytest.raises(AdapterValidationError) as error:
        normalize_source(source_path, "nba-source", "nba_playerstats", 1)

    message = str(error.value)
    assert str(source_path) in message
    assert "adapter nba_playerstats v1" in message
    assert repr(field) in message


def test_invalid_espn_source_id_is_rejected(tmp_path: Path) -> None:
    source_path = _write_parquet(
        tmp_path / "invalid-espn.parquet",
        [{"id": None, "displayName": "No ID"}],
    )

    with pytest.raises(AdapterValidationError) as error:
        normalize_source(source_path, "espn-source", "espn_player_details", 1)

    assert "field 'id'" in str(error.value)
    assert "adapter espn_player_details v1" in str(error.value)
