from __future__ import annotations

import pandas as pd
import pytest

from player_generator.ingest import (
    PLAYER_STATS_REQUIRED_COLUMNS,
    aggregate_player_seasons,
    load_player_stats,
)


def _player_stats_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {column: 0 for column in PLAYER_STATS_REQUIRED_COLUMNS}
    row.update(
        {
            "player_id": 101,
            "player_name": "Synthetic Player",
            "team_id": 10,
            "team_abbreviation": "TST",
            "age": 26.0,
            "gp": 72,
            "min": 2160.0,
            "min_pergame": 30.0,
            "year": 2026,
            "pts_per100possessions": 24.0,
            "usg_pct": 0.22,
            "ts_pct": 0.58,
            "ast_pct": 0.18,
            "ast_ratio": 16.0,
            "ast_to": 2.5,
            "tov_per100possessions": 3.0,
            "oreb_pct": 0.04,
            "dreb_pct": 0.16,
            "off_rating": 114.0,
            "def_rating": 111.0,
            "e_def_rating": 110.5,
            "pie": 0.12,
            "def_ws": 2.4,
            "player_height_inches": 78,
            "player_weight": "212",
            "college": "Example College",
            "country": "Example Country",
            "draft_year": "2021",
            "draft_round": "1",
            "draft_number": "15",
            "fg2a_frequency": 0.58,
            "fg3a_frequency": 0.42,
        }
    )
    row.update(overrides)
    return row


def _write_player_stats(tmp_path, rows: list[dict[str, object]]):
    path = tmp_path / "playerstats.parquet"
    pd.DataFrame(rows).to_parquet(path, index=False)
    return path


def test_load_player_stats_filters_and_maps_seasons(tmp_path, default_config: dict) -> None:
    path = _write_player_stats(
        tmp_path,
        [
            _player_stats_row(player_id=101, player_name="Older Player", year=2024),
            _player_stats_row(player_id=102, player_name="Recent Player", year=2025),
            _player_stats_row(player_id=103, player_name="Current Player", year=2026),
        ],
    )

    result = load_player_stats(path, {2025, 2026}, default_config)

    assert set(result["season_year"]) == {2025, 2026}
    assert set(result["personId"]) == {102, 103}
    assert set(result["personName"]) == {"Recent Player", "Current Player"}
    assert set(result["teamAbbreviation"]) == {"TST"}


def test_load_player_stats_maps_advanced_metrics_and_coerces_weight(
    tmp_path, default_config: dict
) -> None:
    path = _write_player_stats(
        tmp_path,
        [
            _player_stats_row(
                pts_per100possessions=31.5,
                usg_pct=0.287,
                ts_pct=0.621,
                ast_pct=0.244,
                ast_ratio=21.3,
                ast_to=3.1,
                tov_per100possessions=2.7,
                oreb_pct=0.071,
                dreb_pct=0.213,
                off_rating=121.4,
                def_rating=108.6,
                e_def_rating=107.9,
                pie=0.167,
                def_ws=3.8,
                e_tov_pct=8.7,
                fga=400,
                fta=100,
                player_weight="212",
                fg2a_frequency=0.63,
                fg3a_frequency=0.37,
            )
        ],
    )

    player = load_player_stats(path, {2026}, default_config).iloc[0]

    expected = {
        "pointsPer100": 31.5,
        "usagePercentage": 0.287,
        "trueShootingPercentage": 0.621,
        "assistPercentage": 0.244,
        "assistRatio": 21.3,
        "assistTurnoverRatio": 3.1,
        "turnoversPer100": 2.7,
        "offensiveReboundPercentage": 0.071,
        "defensiveReboundPercentage": 0.213,
        "offensiveRating": 121.4,
        "defensiveRating": 108.6,
        "estimatedDefensiveRating": 107.9,
        "playerImpactEstimate": 0.167,
        "defensiveWinShares": 3.8,
        "estimatedTurnoverPercentage": 8.7,
        "freeThrowRate": 0.25,
        "twoPointAttemptFrequency": 0.63,
        "threePointAttemptFrequency": 0.37,
        "weightPounds": 212.0,
    }
    for column, value in expected.items():
        assert player[column] == pytest.approx(value)


def test_load_player_stats_derives_position_groups_without_source_position(
    tmp_path, default_config: dict
) -> None:
    rows = [
        _player_stats_row(player_id=201, player_height_inches=74),
        _player_stats_row(player_id=202, player_height_inches=79),
        _player_stats_row(
            player_id=203,
            player_height_inches=83,
            reb_pct=0.18,
            blk_per100possessions=2.2,
            fg3a_frequency=0.05,
        ),
    ]
    assert all("position" not in row for row in rows)
    path = _write_player_stats(tmp_path, rows)

    result = load_player_stats(path, {2026}, default_config).set_index("personId")

    assert result.loc[201, "positionGroup"] == "guard"
    assert result.loc[202, "positionGroup"] == "wing"
    assert result.loc[203, "positionGroup"] == "big"


def test_load_player_stats_rejects_missing_required_column(
    tmp_path, default_config: dict
) -> None:
    missing_column = "usg_pct"
    assert missing_column in PLAYER_STATS_REQUIRED_COLUMNS
    row = _player_stats_row()
    row.pop(missing_column)
    path = _write_player_stats(tmp_path, [row])

    with pytest.raises(ValueError) as error:
        load_player_stats(path, {2026}, default_config)

    assert "missing" in str(error.value).lower()
    assert missing_column in str(error.value)


def test_load_player_stats_rejects_duplicate_player_seasons(
    tmp_path, default_config: dict
) -> None:
    path = _write_player_stats(
        tmp_path,
        [
            _player_stats_row(player_id=301, year=2026),
            _player_stats_row(player_id=301, year=2026, player_name="Duplicate"),
        ],
    )

    with pytest.raises(ValueError, match="duplicate player-season"):
        load_player_stats(path, {2026}, default_config)


def test_aggregate_player_seasons_ignores_dnp_for_games(default_config: dict) -> None:
    games = pd.DataFrame(
        [
            {
                "season_year": "2023-24",
                "game_date": pd.Timestamp("2024-01-01"),
                "gameId": 1,
                "teamId": 1,
                "teamCity": "Test",
                "teamName": "Team",
                "teamTricode": "TST",
                "personId": 7,
                "personName": "Named Player",
                "position": "G",
                "minutes_decimal": 30.0,
                "played": True,
                "fieldGoalsMade": 5,
                "fieldGoalsAttempted": 10,
                "threePointersMade": 2,
                "threePointersAttempted": 5,
                "freeThrowsMade": 2,
                "freeThrowsAttempted": 2,
                "reboundsOffensive": 1,
                "reboundsDefensive": 3,
                "reboundsTotal": 4,
                "assists": 6,
                "steals": 1,
                "blocks": 0,
                "turnovers": 2,
                "foulsPersonal": 2,
                "points": 14,
                "plusMinusPoints": 4,
            },
            {
                "season_year": "2023-24",
                "game_date": pd.Timestamp("2024-01-03"),
                "gameId": 2,
                "teamId": 1,
                "teamCity": "Test",
                "teamName": "Team",
                "teamTricode": "TST",
                "personId": 7,
                "personName": "Named Player",
                "position": None,
                "minutes_decimal": 0.0,
                "played": False,
                **{column: 0 for column in [
                    "fieldGoalsMade", "fieldGoalsAttempted", "threePointersMade",
                    "threePointersAttempted", "freeThrowsMade", "freeThrowsAttempted",
                    "reboundsOffensive", "reboundsDefensive", "reboundsTotal", "assists",
                    "steals", "blocks", "turnovers", "foulsPersonal", "points",
                    "plusMinusPoints",
                ]},
            },
        ]
    )
    result = aggregate_player_seasons(games, default_config)
    assert result.iloc[0]["games"] == 1
    assert result.iloc[0]["minutesPerGame"] == 30.0
    assert result.iloc[0]["positionGroup"] == "guard"
