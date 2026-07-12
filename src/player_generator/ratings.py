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
            "adjustedTwoPointPercentage": 0.45,
            "twoPointAttemptsPer36": 0.30,
            "freeThrowAttemptsPer36": 0.25,
        },
        "threePointShooting": {
            "adjustedThreePointPercentage": 0.65,
            "threePointAttemptsPer36": 0.35,
        },
        "freeThrowShooting": {"adjustedFreeThrowPercentage": 1.0},
        "scoringVolume": {"pointsPer36": 0.70, "minutesPerGame": 0.30},
        "playmaking": {"assistsPer36": 0.68, "assistTurnoverRatio": 0.32},
        "ballSecurity": {"inverse:turnoverRateProxy": 0.65, "assistTurnoverRatio": 0.35},
        "offensiveRebounding": {"offensiveReboundsPer36": 1.0},
        "defensiveRebounding": {"defensiveReboundsPer36": 1.0},
        "perimeterDefense": {
            "stealsPer36": 0.72,
            "defensiveReboundsPer36": 0.13,
            "plusMinusPer36": 0.15,
        },
        "interiorDefense": {
            "blocksPer36": 0.65,
            "defensiveReboundsPer36": 0.25,
            "plusMinusPer36": 0.10,
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
            "gameScorePer36": 0.58,
            "minutesPerGame": 0.18,
            "trueShootingPercentage": 0.10,
            "plusMinusPer36": 0.08,
            "availability": 0.06,
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
    comparison_season = str(config["reference"]["comparison_season"])
    minimum_minutes = float(config["reference"]["minimum_minutes"])
    snapshot = rated_seasons[
        (rated_seasons["season_year"] == comparison_season)
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
        "heightInches",
        "weightPounds",
        "country",
        "draftYear",
        "games",
        "minutes",
        "minutesPerGame",
        "pointsPer36",
        "assistsPer36",
        "offensiveReboundsPer36",
        "defensiveReboundsPer36",
        "stealsPer36",
        "blocksPer36",
        "turnoversPer36",
        "adjustedTwoPointPercentage",
        "adjustedThreePointPercentage",
        "adjustedFreeThrowPercentage",
        "trueShootingPercentage",
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
