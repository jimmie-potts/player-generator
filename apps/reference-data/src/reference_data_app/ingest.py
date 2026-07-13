from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow.parquet as pq

from reference_data_app.math import safe_divide
from reference_data_app.playerstats_source import (
    PLAYER_STATS_OPTIONAL_COLUMNS,
    PLAYER_STATS_REQUIRED_COLUMNS,
)


def _derive_position_groups(frame: pd.DataFrame) -> pd.Series:
    """Infer replaceable guard/wing/big buckets from physical and role indicators.

    playerstats.parquet does not contain position. These broad buckets are suitable for template
    stratification, but they are not claimed to be authoritative NBA positions.
    """
    height = pd.to_numeric(frame["player_height_inches"], errors="coerce")
    assist_pct = pd.to_numeric(frame["ast_pct"], errors="coerce")
    assist_ratio = pd.to_numeric(frame["ast_ratio"], errors="coerce")
    rebound_pct = pd.to_numeric(frame["reb_pct"], errors="coerce")
    offensive_rebound_pct = pd.to_numeric(frame["oreb_pct"], errors="coerce")
    blocks_per_100 = pd.to_numeric(frame["blk_per100possessions"], errors="coerce")
    three_point_frequency = pd.to_numeric(frame["fg3a_frequency"], errors="coerce")

    groups = pd.Series("wing", index=frame.index, dtype="object")
    guard = (height <= 76) | (
        (height <= 80)
        & (assist_pct >= 0.28)
        & (assist_ratio >= 18.0)
        & (offensive_rebound_pct < 0.04)
    )
    big_role = (
        (rebound_pct >= 0.14)
        | (offensive_rebound_pct >= 0.07)
        | (blocks_per_100 >= 1.8)
    )
    big = (height >= 84) | (
        (height >= 79)
        & big_role
        & ((assist_pct < 0.20) | (three_point_frequency < 0.25))
    ) | (
        (height >= 82)
        & (assist_pct < 0.18)
        & (three_point_frequency < 0.45)
        & ((rebound_pct >= 0.12) | (blocks_per_100 >= 1.4))
    )

    missing_height = height.isna()
    guard |= missing_height & (assist_pct >= 0.20) & (rebound_pct < 0.10)
    big |= missing_height & ((rebound_pct >= 0.15) | (blocks_per_100 >= 2.0))
    groups.loc[guard] = "guard"
    groups.loc[big] = "big"
    return groups


def load_player_stats(
    path: Path,
    seasons: set[int],
    config: dict[str, Any],
) -> pd.DataFrame:
    """Load llimllib/nba_data playerstats.parquet into the internal season schema."""
    if not path.exists():
        raise FileNotFoundError(f"Reference player stats file not found: {path}")

    available = set(pq.read_schema(path).names)
    missing = sorted(set(PLAYER_STATS_REQUIRED_COLUMNS) - available)
    if missing:
        raise ValueError(f"playerstats.parquet is missing required columns: {', '.join(missing)}")

    columns = [
        *PLAYER_STATS_REQUIRED_COLUMNS,
        *(column for column in PLAYER_STATS_OPTIONAL_COLUMNS if column in available),
    ]
    raw = pd.read_parquet(path, columns=columns, engine="pyarrow")
    raw["year"] = pd.to_numeric(raw["year"], errors="coerce").astype("Int64")
    raw = raw[raw["year"].isin(seasons)].copy()

    duplicates = raw.duplicated(subset=["player_id", "year"], keep=False)
    if duplicates.any():
        keys = raw.loc[duplicates, ["player_id", "year"]].drop_duplicates()
        raise ValueError(
            "playerstats.parquet contains duplicate player-season rows: "
            f"{keys.to_dict(orient='records')[:5]}"
        )

    optional_defaults: dict[str, object] = {
        "college": pd.NA,
        "country": pd.NA,
        "draft_year": pd.NA,
        "draft_round": pd.NA,
        "draft_number": pd.NA,
    }
    for column, default in optional_defaults.items():
        if column not in raw:
            raw[column] = default

    numeric_columns = set(PLAYER_STATS_REQUIRED_COLUMNS) - {
        "player_name",
        "team_abbreviation",
        "player_weight",
    }
    for column in numeric_columns:
        raw[column] = pd.to_numeric(raw[column], errors="coerce")

    result = pd.DataFrame(index=raw.index)
    direct_columns = {
        "season_year": "year",
        "personId": "player_id",
        "personName": "player_name",
        "teamAbbreviation": "team_abbreviation",
        "sourceAge": "age",
        "games": "gp",
        "minutes": "min",
        "minutesPerGame": "min_pergame",
        "fieldGoalsMade": "fgm",
        "fieldGoalsAttempted": "fga",
        "threePointersMade": "fg3m",
        "threePointersAttempted": "fg3a",
        "freeThrowsMade": "ftm",
        "freeThrowsAttempted": "fta",
        "reboundsOffensive": "oreb",
        "reboundsDefensive": "dreb",
        "reboundsTotal": "reb",
        "assists": "ast",
        "steals": "stl",
        "blocks": "blk",
        "turnovers": "tov",
        "foulsPersonal": "pf",
        "points": "pts",
        "plusMinusPoints": "plus_minus",
        "twoPointersMade": "fg2m",
        "twoPointersAttempted": "fg2a",
        "twoPointPercentage": "fg2_pct",
        "pointsPer36": "pts_per36",
        "threePointAttemptsPer36": "fg3a_per36",
        "freeThrowAttemptsPer36": "fta_per36",
        "assistsPer36": "ast_per36",
        "turnoversPer36": "tov_per36",
        "offensiveReboundsPer36": "oreb_per36",
        "defensiveReboundsPer36": "dreb_per36",
        "stealsPer36": "stl_per36",
        "blocksPer36": "blk_per36",
        "plusMinusPer36": "plus_minus_per36",
        "pointsPer100": "pts_per100possessions",
        "assistsPer100": "ast_per100possessions",
        "turnoversPer100": "tov_per100possessions",
        "stealsPer100": "stl_per100possessions",
        "blocksPer100": "blk_per100possessions",
        "estimatedOffensiveRating": "e_off_rating",
        "offensiveRating": "off_rating",
        "estimatedDefensiveRating": "e_def_rating",
        "defensiveRating": "def_rating",
        "estimatedNetRating": "e_net_rating",
        "netRating": "net_rating",
        "assistPercentage": "ast_pct",
        "assistTurnoverRatio": "ast_to",
        "assistRatio": "ast_ratio",
        "offensiveReboundPercentage": "oreb_pct",
        "defensiveReboundPercentage": "dreb_pct",
        "reboundPercentage": "reb_pct",
        "estimatedTurnoverPercentage": "e_tov_pct",
        "effectiveFieldGoalPercentage": "efg_pct",
        "trueShootingPercentage": "ts_pct",
        "usagePercentage": "usg_pct",
        "playerImpactEstimate": "pie",
        "defensiveWinShares": "def_ws",
        "defensiveWinSharesPer36": "def_ws_per36",
        "twoPointAttemptFrequency": "fg2a_frequency",
        "threePointAttemptFrequency": "fg3a_frequency",
        "heightInches": "player_height_inches",
    }
    for output, source in direct_columns.items():
        result[output] = raw[source]

    result["weightPounds"] = pd.to_numeric(raw["player_weight"], errors="coerce")
    result["college"] = raw["college"]
    result["country"] = raw["country"]
    result["draftYear"] = pd.to_numeric(raw["draft_year"], errors="coerce").astype("Int64")
    result["draftRound"] = pd.to_numeric(raw["draft_round"], errors="coerce").astype("Int64")
    result["draftNumber"] = pd.to_numeric(raw["draft_number"], errors="coerce").astype("Int64")
    result["bioPosition"] = pd.NA
    result["positionGroup"] = _derive_position_groups(raw)

    result["twoPointAttemptsPer36"] = safe_divide(
        result["twoPointersAttempted"] * 36.0, result["minutes"]
    )
    result["turnoverRateProxy"] = result["estimatedTurnoverPercentage"]
    season_weights = config["reference"].get("season_weights", {})
    result["seasonWeight"] = result["season_year"].map(season_weights).fillna(1.0)

    game_score = (
        result["points"]
        + 0.4 * result["fieldGoalsMade"]
        - 0.7 * result["fieldGoalsAttempted"]
        - 0.4 * (result["freeThrowsAttempted"] - result["freeThrowsMade"])
        + 0.7 * result["reboundsOffensive"]
        + 0.3 * result["reboundsDefensive"]
        + result["steals"]
        + 0.7 * result["assists"]
        + 0.7 * result["blocks"]
        - 0.4 * result["foulsPersonal"]
        - result["turnovers"]
    )
    result["gameScorePer36"] = safe_divide(game_score * 36.0, result["minutes"])
    result["games"] = result["games"].fillna(0).astype(int)
    return result.sort_values(["season_year", "personName"]).reset_index(drop=True)
