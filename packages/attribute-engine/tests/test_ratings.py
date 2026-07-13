from __future__ import annotations

from typing import Any

import pandas as pd
import pytest
from player_attribute_engine.ratings import rate_player_seasons


def _rating_row(name: str, **overrides: Any) -> dict[str, Any]:
    row = {
        "season_year": 2026,
        "personId": name,
        "personName": name,
        "games": 50,
        "twoPointersMade": 40,
        "twoPointersAttempted": 80,
        "threePointersMade": 20,
        "threePointersAttempted": 60,
        "freeThrowsMade": 30,
        "freeThrowsAttempted": 40,
        "fieldGoalsAttempted": 140,
        "adjustedTwoPointPercentage": 0.50,
        "twoPointAttemptFrequency": 0.50,
        "freeThrowRate": 0.25,
        "adjustedThreePointPercentage": 0.35,
        "threePointAttemptFrequency": 0.50,
        "adjustedFreeThrowPercentage": 0.78,
        "pointsPer100": 22.0,
        "usagePercentage": 0.20,
        "trueShootingPercentage": 0.58,
        "assistsPer36": 4.0,
        "assistPercentage": 0.18,
        "assistRatio": 18.0,
        "assistTurnoverRatio": 2.0,
        "estimatedTurnoverPercentage": 10.0,
        "turnoversPer100": 2.5,
        "offensiveReboundPercentage": 0.05,
        "defensiveReboundPercentage": 0.14,
        "stealsPer100": 1.5,
        "blocksPer100": 1.0,
        "estimatedDefensiveRating": 113.0,
        "defensiveWinSharesPer36": 0.10,
        "playerImpactEstimate": 0.10,
        "minutesPerGame": 25.0,
        "minutes": 1500.0,
        "availability": 0.75,
        "estimatedNetRating": 0.0,
    }
    row.update(overrides)
    return row


@pytest.mark.parametrize(
    ("rating", "low", "high"),
    [
        (
            "scoringVolume",
            {"pointsPer100": 16.0, "usagePercentage": 0.14, "trueShootingPercentage": 0.52},
            {"pointsPer100": 32.0, "usagePercentage": 0.29, "trueShootingPercentage": 0.64},
        ),
        (
            "playmaking",
            {"assistsPer36": 2.0, "assistPercentage": 0.08, "assistRatio": 10.0},
            {"assistsPer36": 9.0, "assistPercentage": 0.34, "assistRatio": 30.0},
        ),
        (
            "ballSecurity",
            {
                "estimatedTurnoverPercentage": 16.0,
                "turnoversPer100": 5.0,
                "assistTurnoverRatio": 1.0,
            },
            {
                "estimatedTurnoverPercentage": 6.0,
                "turnoversPer100": 1.2,
                "assistTurnoverRatio": 4.0,
            },
        ),
        (
            "offensiveRebounding",
            {"offensiveReboundPercentage": 0.01},
            {"offensiveReboundPercentage": 0.15},
        ),
        (
            "defensiveRebounding",
            {"defensiveReboundPercentage": 0.06},
            {"defensiveReboundPercentage": 0.25},
        ),
        (
            "interiorDefense",
            {"blocksPer100": 0.2, "estimatedDefensiveRating": 120.0},
            {"blocksPer100": 3.5, "estimatedDefensiveRating": 105.0},
        ),
    ],
)
def test_advanced_metrics_move_ratings_in_expected_direction(
    reference_config: dict,
    rating: str,
    low: dict[str, float],
    high: dict[str, float],
) -> None:
    frame = pd.DataFrame(
        [
            _rating_row("Low", **low),
            _rating_row("High", **high),
        ]
    )

    rated = rate_player_seasons(frame, reference_config).set_index("personName")

    assert rated.loc["High", rating] > rated.loc["Low", rating]


def test_legacy_adapter_groups_seasons_and_keeps_only_complete_templates(
    reference_config: dict,
) -> None:
    frame = pd.DataFrame(
        [
            _rating_row("Shared", season_year=2025, personId=1),
            _rating_row("Shared", season_year=2026, personId=1),
            _rating_row("Incomplete", personId=2, stealsPer100=None),
        ]
    )

    rated = rate_player_seasons(frame, reference_config)

    assert list(rated["season_year"]) == [2025, 2026]
    assert list(rated["personName"]) == ["Shared", "Shared"]
    assert rated["perimeterDefense"].notna().all()
    assert "Incomplete" not in set(rated["personName"])


def test_legacy_adapter_empty_result_keeps_the_rating_schema(
    reference_config: dict,
) -> None:
    source = pd.DataFrame(columns=list(_rating_row("Schema")))

    rated = rate_player_seasons(source, reference_config)

    assert rated.empty
    assert {
        "insideScoring",
        "overall",
        "impactPercentile",
        "talentTier",
        "formulaVersion",
        "adjustedThreePointPercentage",
    } <= set(rated.columns)
