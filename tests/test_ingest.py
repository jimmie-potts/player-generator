from __future__ import annotations

import pandas as pd

from player_generator.ingest import aggregate_player_seasons


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
