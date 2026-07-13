from __future__ import annotations

from typing import Any

import pandas as pd

from player_attribute_engine.contract import FormulaDocument
from player_attribute_engine.evaluator import _evaluate_prepared_player_attributes
from player_attribute_engine.formula import load_formula
from player_attribute_engine.metrics import prepare_formula_metrics


def assign_talent_tier(
    overall: int | float,
    formula: FormulaDocument | None = None,
) -> str:
    """Assign an overall rating using only the active formula's versioned tier ranges."""
    active = formula if formula is not None else load_formula()
    value = float(overall)
    for tier in active.talent_tiers:
        if tier.minimum <= value <= tier.maximum:
            return tier.name
    raise ValueError(f"Overall rating {overall!r} is outside the formula's talent-tier ranges.")


def _evaluation_frame(player_seasons: pd.DataFrame) -> pd.DataFrame:
    frame = player_seasons.reset_index(drop=True).copy()
    if "season" not in frame:
        if "season_year" not in frame:
            raise ValueError("Player-season rows require a season column.")
        frame["season"] = frame["season_year"]
    if "playerId" not in frame:
        if "personId" in frame:
            frame["playerId"] = frame["personId"]
        else:
            raise ValueError("Player-season rows require a playerId or current legacy personId.")
    frame["playerId"] = frame["playerId"].map(
        lambda value: None if pd.isna(value) else str(value)
    )
    return frame


def _empty_rated_frame(
    player_seasons: pd.DataFrame,
    formula: FormulaDocument,
) -> pd.DataFrame:
    result = player_seasons.copy()
    for metric in (
        "adjustedTwoPointPercentage",
        "adjustedThreePointPercentage",
        "adjustedFreeThrowPercentage",
        "freeThrowRate",
        "availability",
    ):
        result[metric] = pd.Series(dtype=float)
    attribute_names = {attribute.name for attribute in formula.attributes}
    for field in formula.output_fields:
        if field == "playerId":
            continue
        if field in attribute_names:
            result[field] = pd.Series(dtype="Int64")
        elif field == "impactPercentile":
            result[field] = pd.Series(dtype=float)
        else:
            result[field] = pd.Series(dtype=object)
    for attribute in formula.attributes:
        if attribute.name != "overall":
            result[f"{attribute.name}Percentile"] = pd.Series(dtype=float)
    return result


def rate_player_seasons(
    player_seasons: pd.DataFrame,
    config: dict[str, Any] | None = None,
) -> pd.DataFrame:
    """Rate the current legacy wide rows through the shared declarative evaluator.

    ``config`` remains accepted while the current reference-data build is a legacy interface, but
    formula behavior no longer comes from application configuration. US-008 will replace this
    compatibility adapter when the roster generator consumes normalized reference packages.
    """
    del config
    formula = load_formula()
    if player_seasons.empty:
        return _empty_rated_frame(player_seasons, formula)

    evaluation_frame = _evaluation_frame(player_seasons)
    prepared_rows: list[pd.DataFrame] = []
    evaluated_rows: list[dict[str, Any] | None] = [None] * len(evaluation_frame)
    explanations: list[dict[str, Any] | None] = [None] * len(evaluation_frame)
    for indices in evaluation_frame.groupby("season", sort=True, dropna=False).groups.values():
        positions = [int(index) for index in indices]
        cohort = evaluation_frame.loc[positions].reset_index(drop=True)
        prepared = prepare_formula_metrics(cohort, formula.metrics)
        prepared["_legacyRowIndex"] = positions
        prepared_rows.append(prepared)
        batch = _evaluate_prepared_player_attributes(prepared, formula)
        for offset, position in enumerate(positions):
            evaluated_rows[position] = batch.rows[offset]
            explanations[position] = batch.explanations[offset]

    if any(row is None for row in evaluated_rows) or any(
        explanation is None for explanation in explanations
    ):
        raise AssertionError("Every legacy player-season row must be evaluated exactly once.")
    output_rows = [row for row in evaluated_rows if row is not None]
    detail_rows = [explanation for explanation in explanations if explanation is not None]
    prepared = (
        pd.concat(prepared_rows, ignore_index=True)
        .sort_values("_legacyRowIndex")
        .reset_index(drop=True)
    )
    result = player_seasons.reset_index(drop=True).copy()

    for metric in (
        "adjustedTwoPointPercentage",
        "adjustedThreePointPercentage",
        "adjustedFreeThrowPercentage",
        "freeThrowRate",
        "availability",
    ):
        result[metric] = prepared[metric]

    for field in formula.output_fields:
        if field == "playerId":
            continue
        result[field] = [row[field] for row in output_rows]

    for attribute in formula.attributes:
        if attribute.name == "overall":
            continue
        result[f"{attribute.name}Percentile"] = [
            explanation["attributes"][attribute.name]["compositePercentile"]
            for explanation in detail_rows
        ]

    rating_fields = [attribute.name for attribute in formula.attributes]
    result = result[result[rating_fields].notna().all(axis=1)].copy()
    for field in rating_fields:
        result[field] = result[field].astype(int)

    sort_columns: list[str] = []
    ascending: list[bool] = []
    if "season_year" in result:
        sort_columns.append("season_year")
        ascending.append(True)
    elif "season" in result:
        sort_columns.append("season")
        ascending.append(True)
    sort_columns.append("overall")
    ascending.append(False)
    if "personName" in result:
        sort_columns.append("personName")
        ascending.append(True)
    return result.sort_values(sort_columns, ascending=ascending).reset_index(drop=True)
