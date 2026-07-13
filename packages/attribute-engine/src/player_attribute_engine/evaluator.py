from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from player_attribute_engine.contract import normalize_component_weights
from player_attribute_engine.metrics import (
    MetricPreparationError,
    prepare_formula_metrics,
    scheduled_value,
)


class EvaluationError(ValueError):
    """Raised when a validated formula cannot evaluate the supplied rows."""


@dataclass(frozen=True)
class EvaluationBatch:
    rows: list[dict[str, Any]]
    explanations: list[dict[str, Any]]

    @property
    def results(self) -> list[dict[str, Any]]:
        """Retain the original read-only name for callers migrating to ``rows``."""
        return self.rows


def _value(item: object, field: str, *alternatives: str) -> Any:
    names = (field, *alternatives)
    if isinstance(item, Mapping):
        for name in names:
            if name in item:
                return item[name]
    else:
        for name in names:
            if hasattr(item, name):
                return getattr(item, name)
    raise EvaluationError(f"Formula object is missing field {field!r}")


def _optional_value(item: object, field: str, *alternatives: str) -> Any:
    try:
        return _value(item, field, *alternatives)
    except EvaluationError:
        return None


def _json_value(value: object) -> Any:
    if value is None or value is pd.NA:
        return None
    if isinstance(value, (np.integer, int)) and not isinstance(value, bool):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return None if not np.isfinite(float(value)) else float(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def _metric_detail(
    frame: pd.DataFrame,
    metrics: Mapping[str, object],
    metric: str,
    index: int,
    cache: dict[tuple[int, str], dict[str, Any]],
    league_averages: dict[tuple[str, float], float],
) -> dict[str, Any]:
    key = (index, metric)
    if key in cache:
        return cache[key]
    definition = metrics[metric]
    kind = str(_value(definition, "kind"))
    value = _json_value(frame.at[index, metric])
    detail: dict[str, Any] = {"kind": kind, "value": value}
    if kind == "input":
        detail["field"] = str(_value(definition, "field"))
    else:
        inputs = tuple(str(item) for item in _value(definition, "inputs"))
        detail["inputs"] = {
            input_name: _metric_detail(
                frame,
                metrics,
                input_name,
                index,
                cache,
                league_averages,
            )
            for input_name in inputs
        }
        if kind == "ratio":
            detail["zeroDenominatorValue"] = 0.0
        elif kind == "stabilizedPercentage":
            detail["priorAttempts"] = float(_value(definition, "prior_attempts"))
            season_value = frame.at[index, "season"]
            detail["season"] = _json_value(season_value)
            if pd.isna(season_value):
                detail["leagueAverage"] = None
            else:
                season = float(season_value)
                average_key = (metric, season)
                if average_key not in league_averages:
                    cohort = frame[frame["season"] == season]
                    valid = cohort[inputs[0]].notna() & cohort[inputs[1]].notna()
                    attempts = float(cohort.loc[valid, inputs[1]].sum())
                    league_averages[average_key] = (
                        float(cohort.loc[valid, inputs[0]].sum()) / attempts
                        if attempts > 0
                        else 0.0
                    )
                detail["leagueAverage"] = league_averages[average_key]
        elif kind == "scheduledRatio":
            detail["scheduledGames"] = _json_value(
                scheduled_value(_value(definition, "schedule"), frame.at[index, inputs[1]])
            )
            detail["minimum"] = 0.0
            detail["maximum"] = 1.0
    cache[key] = detail
    return detail


def _unique(values: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _groups(frame: pd.DataFrame, fields: Sequence[str]) -> list[list[int]]:
    valid = frame[list(fields)].notna().all(axis=1)
    if not valid.any():
        return []
    grouper: str | list[str] = fields[0] if len(fields) == 1 else list(fields)
    return [
        [int(index) for index in indices]
        for indices in frame.loc[valid].groupby(grouper, sort=True).groups.values()
    ]


def _validate_population(
    frame: pd.DataFrame,
    attributes: Sequence[object],
    cohorts: Mapping[str, object],
) -> None:
    invalid_ids = frame["playerId"].map(
        lambda value: not isinstance(value, str) or not value.strip()
    )
    if invalid_ids.any():
        rows = ", ".join(str(index) for index in frame.index[invalid_ids][:5])
        raise EvaluationError(
            "Formula evaluation requires non-empty string playerId values; "
            f"invalid rows: {rows}"
        )
    duplicate_ids = frame["playerId"].duplicated(keep=False)
    if duplicate_ids.any():
        values = ", ".join(
            str(value) for value in frame.loc[duplicate_ids, "playerId"].drop_duplicates()[:5]
        )
        raise EvaluationError(
            "Formula evaluation requires one row per player in a cohort; "
            f"duplicate playerId values: {values}"
        )

    cohort_names = _unique([str(_value(attribute, "cohort")) for attribute in attributes])
    for cohort_name in cohort_names:
        fields = tuple(str(field) for field in _value(cohorts[cohort_name], "group_by"))
        complete = frame[list(fields)].dropna()
        if len(complete.drop_duplicates()) > 1:
            raise EvaluationError(
                "Formula evaluation accepts one percentile cohort per call; "
                f"cohort {cohort_name!r} varies across fields: {', '.join(fields)}"
            )


def _eligibility(
    frame: pd.DataFrame,
    attribute: object,
    eligibility_rules: Mapping[str, object],
    cohorts: Mapping[str, object],
) -> tuple[pd.Series, list[list[dict[str, Any]]], tuple[str, ...]]:
    rule_name = str(_value(attribute, "eligibility_rule"))
    cohort_name = str(_value(attribute, "cohort"))
    rule = eligibility_rules[rule_name]
    cohort = cohorts[cohort_name]
    group_by = tuple(str(field) for field in _value(cohort, "group_by"))
    components = tuple(_value(attribute, "components"))
    component_metrics = [str(_value(component, "metric")) for component in components]
    minimum_samples = _value(rule, "minimum_samples")
    required = _unique(
        [
            *(str(metric) for metric in _value(rule, "required_metrics")),
            *(str(metric) for metric in minimum_samples),
            *component_metrics,
        ]
    )

    eligible = pd.Series(True, index=frame.index, dtype=bool)
    reasons: list[list[dict[str, Any]]] = [[] for _ in frame.index]
    for metric in required:
        missing = frame[metric].isna()
        eligible &= ~missing
        for index in frame.index[missing]:
            reasons[int(index)].append({"kind": "missingMetric", "metric": metric})

    for metric, minimum in minimum_samples.items():
        present = frame[str(metric)].notna()
        below = present & (frame[str(metric)] < float(minimum))
        eligible &= ~below
        for index in frame.index[below]:
            reasons[int(index)].append(
                {
                    "kind": "minimumSample",
                    "metric": str(metric),
                    "minimum": _json_value(minimum),
                    "actual": _json_value(frame.at[index, str(metric)]),
                }
            )

    for field in group_by:
        missing = frame[field].isna()
        eligible &= ~missing
        for index in frame.index[missing]:
            reasons[int(index)].append({"kind": "missingCohort", "metric": field})
    return eligible, reasons, group_by


def _rating(percentiles: pd.Series, scale: object) -> pd.Series:
    anchors = tuple(_value(scale, "anchors"))

    def anchor_value(anchor: object, field: str, position: int) -> float:
        if (
            isinstance(anchor, Sequence)
            and not isinstance(anchor, (str, bytes))
            and len(anchor) == 2
        ):
            return float(anchor[position])
        return float(_value(anchor, field))

    anchor_percentiles = np.asarray(
        [anchor_value(anchor, "percentile", 0) for anchor in anchors], dtype=float
    )
    anchor_ratings = np.asarray(
        [anchor_value(anchor, "rating", 1) for anchor in anchors], dtype=float
    )
    values = np.interp(percentiles.to_numpy(dtype=float), anchor_percentiles, anchor_ratings)
    rounded = np.rint(values)
    bounded = np.clip(
        rounded,
        float(_value(scale, "minimum")),
        float(_value(scale, "maximum")),
    )
    return pd.Series(bounded, index=percentiles.index, dtype=float)


def _tier_for(rating: int, tiers: Sequence[object]) -> str:
    for tier in tiers:
        if float(_value(tier, "minimum")) <= rating <= float(_value(tier, "maximum")):
            return str(_value(tier, "name"))
    raise EvaluationError(f"Overall rating {rating} is outside every configured talent tier")


def evaluate_player_attributes(frame: pd.DataFrame, formula: object) -> EvaluationBatch:
    """Evaluate one season cohort through a declarative formula document."""
    if "playerId" not in frame.columns:
        raise EvaluationError("Formula evaluation is missing required input column: playerId")

    metrics = _value(formula, "metrics")
    try:
        prepared = prepare_formula_metrics(frame, metrics)
    except MetricPreparationError as error:
        raise EvaluationError(str(error)) from error

    return _evaluate_prepared_player_attributes(prepared, formula)


def _evaluate_prepared_player_attributes(
    prepared: pd.DataFrame,
    formula: object,
) -> EvaluationBatch:
    """Evaluate a cohort whose formula metrics have already been materialized."""
    metrics = _value(formula, "metrics")

    output_fields = tuple(str(field) for field in _value(formula, "output_fields"))
    formula_version = str(_value(formula, "formula_version"))
    attributes = tuple(_value(formula, "attributes"))
    eligibility_rules = _value(formula, "eligibility_rules", "eligibility")
    cohorts = _value(formula, "cohorts")
    rating_scales = _value(formula, "rating_scales", "scales")
    tiers = tuple(_value(formula, "talent_tiers", "tiers"))

    _validate_population(prepared, attributes, cohorts)

    rows = [{field: None for field in output_fields} for _ in prepared.index]
    details: list[dict[str, Any]] = []
    metric_detail_cache: dict[tuple[int, str], dict[str, Any]] = {}
    league_averages: dict[tuple[str, float], float] = {}
    for index in prepared.index:
        rows[int(index)]["playerId"] = _json_value(prepared.at[index, "playerId"])
        rows[int(index)]["formulaVersion"] = formula_version
        details.append(
            {
                "playerId": rows[int(index)]["playerId"],
                "season": _json_value(prepared.at[index, "season"])
                if "season" in prepared
                else None,
                "formulaVersion": formula_version,
                "attributes": {},
            }
        )

    for attribute in attributes:
        name = str(_value(attribute, "name"))
        components = tuple(_value(attribute, "components"))
        eligible, reasons, group_by = _eligibility(
            prepared, attribute, eligibility_rules, cohorts
        )
        scale_name = str(_value(attribute, "rating_scale"))
        scale = rating_scales[scale_name]
        weights = {
            str(_value(component, "metric")): float(_value(component, "weight"))
            for component in components
        }
        try:
            normalized_values = normalize_component_weights(tuple(weights.values()))
        except ValueError as error:
            raise EvaluationError(f"Attribute {name!r} component {error}") from error
        normalized_weights = dict(zip(weights, normalized_values, strict=True))
        component_percentiles = {
            metric: pd.Series(np.nan, index=prepared.index, dtype=float)
            for metric in weights
        }
        contributions = {
            metric: pd.Series(np.nan, index=prepared.index, dtype=float)
            for metric in weights
        }
        composite = pd.Series(np.nan, index=prepared.index, dtype=float)
        composite_percentile = pd.Series(np.nan, index=prepared.index, dtype=float)
        ratings = pd.Series(np.nan, index=prepared.index, dtype=float)
        eligible_counts = pd.Series(0, index=prepared.index, dtype=int)

        for indices in _groups(prepared, group_by):
            ranked_indices = [index for index in indices if bool(eligible.at[index])]
            eligible_counts.loc[indices] = len(ranked_indices)
            if not ranked_indices:
                continue
            for component in components:
                metric = str(_value(component, "metric"))
                direction = str(_value(component, "direction"))
                percentiles = prepared.loc[ranked_indices, metric].rank(
                    method="average",
                    pct=True,
                    ascending=direction == "higher",
                )
                component_percentiles[metric].loc[ranked_indices] = percentiles
                contributions[metric].loc[ranked_indices] = (
                    percentiles * normalized_weights[metric]
                )

            composite.loc[ranked_indices] = sum(
                contribution.loc[ranked_indices] for contribution in contributions.values()
            )
            if bool(_value(attribute, "rerank_composite")):
                composite_percentile.loc[ranked_indices] = composite.loc[ranked_indices].rank(
                    method="average", pct=True, ascending=True
                )
            else:
                composite_percentile.loc[ranked_indices] = composite.loc[ranked_indices]
            ratings.loc[ranked_indices] = _rating(
                composite_percentile.loc[ranked_indices], scale
            )

        percentile_output = _optional_value(attribute, "percentile_output")
        for index in prepared.index:
            rating = None if pd.isna(ratings.at[index]) else int(ratings.at[index])
            percentile = _json_value(composite_percentile.at[index])
            rows[int(index)][name] = rating
            if percentile_output is not None:
                rows[int(index)][str(percentile_output)] = percentile
            if name == "overall" and rating is not None:
                rows[int(index)]["talentTier"] = _tier_for(rating, tiers)

            cohort_values = {
                field: _json_value(prepared.at[index, field]) for field in group_by
            }
            details[int(index)]["attributes"][name] = {
                "eligible": bool(eligible.at[index]),
                "ineligibilityReasons": reasons[int(index)],
                "cohort": {
                    "name": str(_value(attribute, "cohort")),
                    "values": cohort_values,
                    "eligibleCount": int(eligible_counts.at[index]),
                },
                "rawInputs": {
                    metric: _json_value(prepared.at[index, metric]) for metric in weights
                },
                "metricDetails": {
                    metric: _metric_detail(
                        prepared,
                        metrics,
                        metric,
                        int(index),
                        metric_detail_cache,
                        league_averages,
                    )
                    for metric in weights
                },
                "componentPercentiles": {
                    metric: _json_value(values.at[index])
                    for metric, values in component_percentiles.items()
                },
                "normalizedWeights": normalized_weights,
                "contributions": {
                    metric: _json_value(values.at[index])
                    for metric, values in contributions.items()
                },
                "composite": _json_value(composite.at[index]),
                "compositePercentile": percentile,
                "rating": rating,
            }

    return EvaluationBatch(rows=rows, explanations=details)
