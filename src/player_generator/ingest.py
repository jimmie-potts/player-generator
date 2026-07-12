from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

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

    for season, indices in result.groupby("season_year").groups.items():
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
