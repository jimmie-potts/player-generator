from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from player_generator.util import parse_minutes, safe_divide

BOX_SCORE_COLUMNS = (
    "season_year",
    "game_date",
    "gameId",
    "teamId",
    "teamCity",
    "teamName",
    "teamTricode",
    "personId",
    "personName",
    "position",
    "comment",
    "minutes",
    "fieldGoalsMade",
    "fieldGoalsAttempted",
    "threePointersMade",
    "threePointersAttempted",
    "freeThrowsMade",
    "freeThrowsAttempted",
    "reboundsOffensive",
    "reboundsDefensive",
    "reboundsTotal",
    "assists",
    "steals",
    "blocks",
    "turnovers",
    "foulsPersonal",
    "points",
    "plusMinusPoints",
)

COUNTING_COLUMNS = (
    "fieldGoalsMade",
    "fieldGoalsAttempted",
    "threePointersMade",
    "threePointersAttempted",
    "freeThrowsMade",
    "freeThrowsAttempted",
    "reboundsOffensive",
    "reboundsDefensive",
    "reboundsTotal",
    "assists",
    "steals",
    "blocks",
    "turnovers",
    "foulsPersonal",
    "points",
    "plusMinusPoints",
)


# The projected upstream schema used by the first-pass playerstats.parquet adapter. Keeping this
# list explicit makes upstream schema drift fail early and avoids loading 235 columns into memory.
PLAYER_STATS_REQUIRED_COLUMNS = (
    "player_id",
    "player_name",
    "team_abbreviation",
    "age",
    "gp",
    "min",
    "fgm",
    "fga",
    "fg3m",
    "fg3a",
    "ftm",
    "fta",
    "oreb",
    "dreb",
    "reb",
    "ast",
    "tov",
    "stl",
    "blk",
    "pf",
    "pts",
    "plus_minus",
    "year",
    "min_pergame",
    "fg3a_per36",
    "fta_per36",
    "oreb_per36",
    "dreb_per36",
    "ast_per36",
    "tov_per36",
    "stl_per36",
    "blk_per36",
    "pts_per36",
    "plus_minus_per36",
    "pts_per100possessions",
    "ast_per100possessions",
    "tov_per100possessions",
    "stl_per100possessions",
    "blk_per100possessions",
    "e_off_rating",
    "off_rating",
    "e_def_rating",
    "def_rating",
    "e_net_rating",
    "net_rating",
    "ast_pct",
    "ast_to",
    "ast_ratio",
    "oreb_pct",
    "dreb_pct",
    "reb_pct",
    "e_tov_pct",
    "efg_pct",
    "ts_pct",
    "usg_pct",
    "pie",
    "def_ws",
    "def_ws_per36",
    "fg2m",
    "fg2a",
    "fg2_pct",
    "fg2a_frequency",
    "fg3a_frequency",
    "player_height_inches",
    "player_weight",
)

PLAYER_STATS_OPTIONAL_COLUMNS = (
    "college",
    "country",
    "draft_year",
    "draft_round",
    "draft_number",
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
    result["freeThrowRate"] = safe_divide(
        result["freeThrowsAttempted"], result["fieldGoalsAttempted"]
    )
    result["turnoverRateProxy"] = result["estimatedTurnoverPercentage"]

    scheduled_games = config["reference"].get("scheduled_games", {})
    result["scheduledGames"] = result["season_year"].map(scheduled_games).fillna(82).astype(int)
    result["availability"] = safe_divide(result["games"], result["scheduledGames"]).clip(0, 1)
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
    result = _add_stabilized_percentages(result, config)
    result["games"] = result["games"].fillna(0).astype(int)
    return result.sort_values(["season_year", "personName"]).reset_index(drop=True)


def load_box_scores(paths: Iterable[Path], seasons: set[str] | None = None) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path in paths:
        if not path.exists():
            raise FileNotFoundError(f"Reference box score file not found: {path}")
        frame = pd.read_csv(path, usecols=lambda c: c in BOX_SCORE_COLUMNS, low_memory=False)
        if seasons:
            frame = frame[frame["season_year"].isin(seasons)]
        frames.append(frame)

    if not frames:
        raise ValueError("No reference box score files were supplied.")

    games = pd.concat(frames, ignore_index=True)
    games = games.drop_duplicates(subset=["gameId", "teamId", "personId"], keep="last")
    games["minutes_decimal"] = games["minutes"].map(parse_minutes).astype(float)
    games["game_date"] = pd.to_datetime(games["game_date"], errors="coerce")

    for column in COUNTING_COLUMNS:
        games[column] = pd.to_numeric(games[column], errors="coerce").fillna(0.0)

    games["played"] = games["minutes_decimal"] > 0
    return games


def _position_group(position_values: pd.Series, minute_values: pd.Series) -> str:
    weights: Counter[str] = Counter()
    for position, minutes in zip(position_values, minute_values, strict=False):
        if pd.isna(position):
            continue
        text = str(position).upper()
        weight = max(float(minutes), 1.0)
        if "G" in text:
            weights["guard"] += weight
        if "F" in text:
            weights["wing"] += weight
        if "C" in text:
            weights["big"] += weight

    if not weights:
        return "unknown"
    priority = {"guard": 2, "wing": 1, "big": 0}
    return max(weights, key=lambda key: (weights[key], priority[key]))


def _latest_value(group: pd.DataFrame, column: str) -> Any:
    valid = group.dropna(subset=[column]).sort_values("game_date")
    return valid.iloc[-1][column] if not valid.empty else None


def _height_to_inches(value: object) -> float:
    if value is None or pd.isna(value):
        return np.nan
    text = str(value).strip()
    if "-" not in text:
        return pd.to_numeric(text, errors="coerce")
    feet, inches = text.split("-", 1)
    try:
        return float(feet) * 12.0 + float(inches)
    except ValueError:
        return np.nan


def load_bio_index(path: Path | None) -> pd.DataFrame:
    columns = [
        "personId",
        "bioPosition",
        "heightInches",
        "weightPounds",
        "country",
        "draftYear",
        "fromYear",
        "toYear",
    ]
    if path is None or not path.exists():
        return pd.DataFrame(columns=columns)

    bio = pd.read_csv(path, low_memory=False)
    wanted = {
        "PERSON_ID": "personId",
        "POSITION": "bioPosition",
        "HEIGHT": "heightRaw",
        "WEIGHT": "weightPounds",
        "COUNTRY": "country",
        "DRAFT_YEAR": "draftYear",
        "FROM_YEAR": "fromYear",
        "TO_YEAR": "toYear",
    }
    available = {key: value for key, value in wanted.items() if key in bio.columns}
    bio = bio[list(available)].rename(columns=available)
    bio = bio.drop_duplicates(subset=["personId"], keep="last")
    bio["personId"] = pd.to_numeric(bio["personId"], errors="coerce")
    bio["heightInches"] = bio.pop("heightRaw").map(_height_to_inches)
    bio["weightPounds"] = pd.to_numeric(bio["weightPounds"], errors="coerce")
    return bio[columns]


def aggregate_player_seasons(
    games: pd.DataFrame,
    config: dict[str, Any],
    bio: pd.DataFrame | None = None,
) -> pd.DataFrame:
    group_keys = ["season_year", "personId", "personName"]
    totals = (
        games.groupby(group_keys, as_index=False)
        .agg(
            games=("played", "sum"),
            minutes=("minutes_decimal", "sum"),
            fieldGoalsMade=("fieldGoalsMade", "sum"),
            fieldGoalsAttempted=("fieldGoalsAttempted", "sum"),
            threePointersMade=("threePointersMade", "sum"),
            threePointersAttempted=("threePointersAttempted", "sum"),
            freeThrowsMade=("freeThrowsMade", "sum"),
            freeThrowsAttempted=("freeThrowsAttempted", "sum"),
            reboundsOffensive=("reboundsOffensive", "sum"),
            reboundsDefensive=("reboundsDefensive", "sum"),
            reboundsTotal=("reboundsTotal", "sum"),
            assists=("assists", "sum"),
            steals=("steals", "sum"),
            blocks=("blocks", "sum"),
            turnovers=("turnovers", "sum"),
            foulsPersonal=("foulsPersonal", "sum"),
            points=("points", "sum"),
            plusMinusPoints=("plusMinusPoints", "sum"),
        )
        .reset_index(drop=True)
    )

    metadata_rows: list[dict[str, Any]] = []
    for keys, group in games.groupby(group_keys, sort=False):
        season, person_id, person_name = keys
        metadata_rows.append(
            {
                "season_year": season,
                "personId": person_id,
                "personName": person_name,
                "positionGroup": _position_group(group["position"], group["minutes_decimal"]),
                "teamAbbreviation": _latest_value(group, "teamTricode"),
                "teamCity": _latest_value(group, "teamCity"),
                "teamName": _latest_value(group, "teamName"),
            }
        )
    metadata = pd.DataFrame(metadata_rows)
    result = totals.merge(metadata, on=group_keys, how="left")

    if bio is not None and not bio.empty:
        result = result.merge(bio, on="personId", how="left")
        unknown = result["positionGroup"].eq("unknown")
        result.loc[unknown, "positionGroup"] = result.loc[unknown, "bioPosition"].map(
            lambda value: _position_group(pd.Series([value]), pd.Series([1.0]))
        )
    else:
        for column in (
            "bioPosition",
            "heightInches",
            "weightPounds",
            "country",
            "draftYear",
            "fromYear",
            "toYear",
        ):
            result[column] = np.nan

    result["games"] = result["games"].astype(int)
    result["minutesPerGame"] = safe_divide(result["minutes"], result["games"])
    result["twoPointersMade"] = result["fieldGoalsMade"] - result["threePointersMade"]
    result["twoPointersAttempted"] = (
        result["fieldGoalsAttempted"] - result["threePointersAttempted"]
    )

    per36_inputs = {
        "pointsPer36": "points",
        "twoPointAttemptsPer36": "twoPointersAttempted",
        "threePointAttemptsPer36": "threePointersAttempted",
        "freeThrowAttemptsPer36": "freeThrowsAttempted",
        "assistsPer36": "assists",
        "turnoversPer36": "turnovers",
        "offensiveReboundsPer36": "reboundsOffensive",
        "defensiveReboundsPer36": "reboundsDefensive",
        "stealsPer36": "steals",
        "blocksPer36": "blocks",
        "foulsPer36": "foulsPersonal",
        "plusMinusPer36": "plusMinusPoints",
    }
    for output, source in per36_inputs.items():
        result[output] = safe_divide(result[source] * 36.0, result["minutes"])

    result["assistTurnoverRatio"] = safe_divide(
        result["assists"], result["turnovers"].replace(0, np.nan), default=0.0
    )
    possessions_proxy = (
        result["fieldGoalsAttempted"]
        + 0.44 * result["freeThrowsAttempted"]
        + result["assists"]
        + result["turnovers"]
    )
    result["turnoverRateProxy"] = safe_divide(result["turnovers"], possessions_proxy)
    result["trueShootingPercentage"] = safe_divide(
        result["points"],
        2.0 * (result["fieldGoalsAttempted"] + 0.44 * result["freeThrowsAttempted"]),
    )

    scheduled_games = config["reference"].get("scheduled_games", {})
    result["scheduledGames"] = result["season_year"].map(scheduled_games).fillna(82).astype(int)
    result["availability"] = safe_divide(result["games"], result["scheduledGames"]).clip(0.0, 1.0)

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

    result = _add_stabilized_percentages(result, config)
    return result.sort_values(["season_year", "personName"]).reset_index(drop=True)


def _add_stabilized_percentages(
    player_seasons: pd.DataFrame, config: dict[str, Any]
) -> pd.DataFrame:
    result = player_seasons.copy()
    priors = config["reference"]["prior_attempts"]

    for _season, indices in result.groupby("season_year").groups.items():
        frame = result.loc[indices]
        pairs = (
            (
                "twoPointersMade",
                "twoPointersAttempted",
                "adjustedTwoPointPercentage",
                float(priors["two_point"]),
            ),
            (
                "threePointersMade",
                "threePointersAttempted",
                "adjustedThreePointPercentage",
                float(priors["three_point"]),
            ),
            (
                "freeThrowsMade",
                "freeThrowsAttempted",
                "adjustedFreeThrowPercentage",
                float(priors["free_throw"]),
            ),
        )
        for made, attempted, output, prior_attempts in pairs:
            total_attempts = float(frame[attempted].sum())
            league_average = (
                float(frame[made].sum()) / total_attempts if total_attempts > 0 else 0.0
            )
            result.loc[indices, output] = (
                frame[made] + league_average * prior_attempts
            ) / (frame[attempted] + prior_attempts)

    return result
