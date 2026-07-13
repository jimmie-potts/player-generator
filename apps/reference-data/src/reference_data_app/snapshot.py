from __future__ import annotations

from typing import Any

import pandas as pd
from player_data_contracts.models import RATING_FIELDS


def build_reference_snapshot(
    rated_seasons: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    comparison_season = int(config["reference"]["comparison_season"])
    minimum_games = int(config["reference"].get("minimum_games", 0))
    minimum_minutes = float(config["reference"]["minimum_minutes"])
    snapshot = rated_seasons[
        (rated_seasons["season_year"] == comparison_season)
        & (rated_seasons["games"] >= minimum_games)
        & (rated_seasons["minutes"] >= minimum_minutes)
        & (rated_seasons["positionGroup"] != "unknown")
    ].copy()
    snapshot["sourcePlayerId"] = snapshot["personId"].astype("Int64")
    snapshot["sourcePlayerName"] = snapshot["personName"]

    columns = [
        "season_year",
        "sourcePlayerId",
        "sourcePlayerName",
        "teamAbbreviation",
        "positionGroup",
        "bioPosition",
        "sourceAge",
        "heightInches",
        "weightPounds",
        "college",
        "country",
        "draftYear",
        "draftRound",
        "draftNumber",
        "games",
        "minutes",
        "minutesPerGame",
        "seasonWeight",
        "pointsPer36",
        "pointsPer100",
        "assistsPer36",
        "assistsPer100",
        "turnoversPer100",
        "usagePercentage",
        "assistPercentage",
        "assistRatio",
        "assistTurnoverRatio",
        "estimatedTurnoverPercentage",
        "offensiveReboundsPer36",
        "defensiveReboundsPer36",
        "offensiveReboundPercentage",
        "defensiveReboundPercentage",
        "stealsPer36",
        "blocksPer36",
        "stealsPer100",
        "blocksPer100",
        "turnoversPer36",
        "adjustedTwoPointPercentage",
        "adjustedThreePointPercentage",
        "adjustedFreeThrowPercentage",
        "twoPointAttemptFrequency",
        "threePointAttemptFrequency",
        "trueShootingPercentage",
        "effectiveFieldGoalPercentage",
        "offensiveRating",
        "defensiveRating",
        "netRating",
        "estimatedOffensiveRating",
        "estimatedDefensiveRating",
        "estimatedNetRating",
        "playerImpactEstimate",
        "defensiveWinShares",
        "availability",
        "gameScorePer36",
        *RATING_FIELDS,
        "overall",
        "impactPercentile",
        "talentTier",
    ]
    return snapshot[columns].sort_values(
        ["overall", "sourcePlayerName"], ascending=[False, True]
    ).reset_index(drop=True)
