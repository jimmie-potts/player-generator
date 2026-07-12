from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from player_generator.schema import RATING_FIELDS, TIER_ORDER
from player_generator.util import interpolate_rating, stable_rank_percentile


def _weighted_percentiles(frame: pd.DataFrame, components: dict[str, float]) -> pd.Series:
    total_weight = sum(components.values())
    if total_weight <= 0:
        raise ValueError("Rating component weights must sum to a positive value.")
    result = pd.Series(0.0, index=frame.index)
    for metric, weight in components.items():
        higher_is_better = True
        if metric.startswith("inverse:"):
            metric = metric.removeprefix("inverse:")
            higher_is_better = False
        result += stable_rank_percentile(frame[metric], higher_is_better) * weight
    return result / total_weight


def _map_skill(percentile: pd.Series, config: dict[str, Any]) -> np.ndarray:
    anchors = config["ratings"]["skill_percentile_anchors"]
    return interpolate_rating(percentile, anchors["percentiles"], anchors["ratings"])


def _map_overall(percentile: pd.Series, config: dict[str, Any]) -> np.ndarray:
    anchors = config["ratings"]["overall_percentile_anchors"]
    return interpolate_rating(percentile, anchors["percentiles"], anchors["ratings"])


def assign_talent_tier(overall: int | float, config: dict[str, Any]) -> str:
    bounds = config["league_generation"]["tier_bounds"]
    value = float(overall)
    for tier in TIER_ORDER:
        low, high = bounds[tier]
        if float(low) <= value <= float(high):
            return tier
    return "superstar" if value > bounds["superstar"][1] else "fringe"


def _rate_one_season(frame: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    result = frame.copy()
    skill_components: dict[str, dict[str, float]] = {
        "insideScoring": {
            "adjustedTwoPointPercentage": 0.50,
            "twoPointAttemptFrequency": 0.30,
            "freeThrowRate": 0.20,
        },
        "threePointShooting": {
            "adjustedThreePointPercentage": 0.60,
            "threePointAttemptFrequency": 0.40,
        },
        "freeThrowShooting": {"adjustedFreeThrowPercentage": 1.0},
        "scoringVolume": {
            "pointsPer100": 0.50,
            "usagePercentage": 0.30,
            "trueShootingPercentage": 0.20,
        },
        "playmaking": {
            "assistsPer36": 0.25,
            "assistPercentage": 0.30,
            "assistRatio": 0.15,
            "assistTurnoverRatio": 0.15,
            "usagePercentage": 0.15,
        },
        "ballSecurity": {
            "inverse:estimatedTurnoverPercentage": 0.40,
            "assistTurnoverRatio": 0.30,
            "inverse:turnoversPer100": 0.30,
        },
        "offensiveRebounding": {"offensiveReboundPercentage": 1.0},
        "defensiveRebounding": {"defensiveReboundPercentage": 1.0},
        "perimeterDefense": {
            "stealsPer100": 0.45,
            "inverse:estimatedDefensiveRating": 0.20,
            "defensiveWinSharesPer36": 0.15,
            "defensiveReboundPercentage": 0.10,
            "playerImpactEstimate": 0.10,
        },
        "interiorDefense": {
            "blocksPer100": 0.35,
            "defensiveReboundPercentage": 0.25,
            "inverse:estimatedDefensiveRating": 0.20,
            "defensiveWinSharesPer36": 0.10,
            "playerImpactEstimate": 0.10,
        },
        "stamina": {"minutesPerGame": 0.80, "minutes": 0.20},
        "durability": {"availability": 1.0},
    }

    for rating, components in skill_components.items():
        composite = _weighted_percentiles(result, components)
        percentile = stable_rank_percentile(composite, higher_is_better=True)
        result[f"{rating}Percentile"] = percentile
        result[rating] = np.rint(_map_skill(percentile, config)).astype(int)

    impact_composite = _weighted_percentiles(
        result,
        {
            "playerImpactEstimate": 0.35,
            "estimatedNetRating": 0.20,
            "pointsPer100": 0.15,
            "minutesPerGame": 0.12,
            "trueShootingPercentage": 0.10,
            "availability": 0.08,
        },
    )
    impact_percentile = stable_rank_percentile(impact_composite, higher_is_better=True)
    result["impactPercentile"] = impact_percentile
    result["overall"] = np.rint(_map_overall(impact_percentile, config)).astype(int)
    result["talentTier"] = result["overall"].map(lambda value: assign_talent_tier(value, config))

    minimum = int(config["ratings"]["minimum"])
    maximum = int(config["ratings"]["maximum"])
    for field in (*RATING_FIELDS, "overall"):
        result[field] = result[field].clip(minimum, maximum).astype(int)
    return result


def rate_player_seasons(player_seasons: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rated = [
        _rate_one_season(frame, config)
        for _, frame in player_seasons.groupby("season_year", sort=True)
    ]
    if not rated:
        return player_seasons.copy()
    return pd.concat(rated, ignore_index=True).sort_values(
        ["season_year", "overall", "personName"], ascending=[True, False, True]
    )


def build_reference_snapshot(rated_seasons: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
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
