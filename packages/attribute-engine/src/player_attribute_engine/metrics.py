from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np
import pandas as pd


class MetricPreparationError(ValueError):
    """Raised when formula metrics cannot be prepared from an input cohort."""


def _value(definition: object, field: str) -> Any:
    if isinstance(definition, Mapping):
        return definition.get(field)
    return getattr(definition, field)


def _numeric(series: pd.Series, field: str) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce").astype(float)
    boolean = series.map(lambda value: isinstance(value, (bool, np.bool_)))
    invalid = series.notna() & (boolean | numeric.isna() | ~np.isfinite(numeric))
    if invalid.any():
        rows = ", ".join(str(index) for index in series.index[invalid][:5])
        raise MetricPreparationError(
            f"Formula input {field!r} must contain finite numeric values or null; "
            f"invalid rows: {rows}"
        )
    return numeric


def _validate_derived(series: pd.Series, metric: str) -> pd.Series:
    invalid = series.notna() & ~np.isfinite(series)
    if invalid.any():
        rows = ", ".join(str(index) for index in series.index[invalid][:5])
        raise MetricPreparationError(
            f"Derived formula metric {metric!r} produced non-finite values at rows: {rows}"
        )
    return series


def required_input_fields(metrics: Mapping[str, object]) -> set[str]:
    """Return every source column named by an input metric."""
    return {
        str(_value(definition, "field"))
        for definition in metrics.values()
        if _value(definition, "kind") == "input"
    }


def _schedule_value(schedule: Mapping[object, object], season: object) -> float | None:
    if pd.isna(season):
        return None
    candidates: list[object] = [season, str(season)]
    try:
        numeric = float(season)
    except (TypeError, ValueError):
        numeric = None
    if numeric is not None and numeric.is_integer():
        candidates.extend((int(numeric), str(int(numeric))))
    for candidate in candidates:
        if candidate in schedule:
            return float(schedule[candidate])
    return None


def _ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    result = numerator / denominator
    zero_denominator = (denominator == 0) & numerator.notna()
    return result.mask(zero_denominator, 0.0).where(
        numerator.notna() & denominator.notna()
    )


def _stabilized_percentage(
    made: pd.Series,
    attempted: pd.Series,
    season: pd.Series,
    prior_attempts: float,
) -> pd.Series:
    result = pd.Series(np.nan, index=made.index, dtype=float)
    groups = season.groupby(season, sort=True, dropna=False).groups
    for season_value, indices in groups.items():
        if pd.isna(season_value):
            continue
        group_made = made.loc[indices]
        group_attempted = attempted.loc[indices]
        valid = group_made.notna() & group_attempted.notna()
        total_attempts = float(group_attempted.loc[valid].sum())
        league_average = (
            float(group_made.loc[valid].sum()) / total_attempts
            if total_attempts > 0
            else 0.0
        )
        result.loc[indices] = (
            group_made + league_average * prior_attempts
        ) / (group_attempted + prior_attempts)
    return result


def prepare_formula_metrics(
    frame: pd.DataFrame,
    metrics: Mapping[str, object],
) -> pd.DataFrame:
    """Materialize validated input and derived metrics without applying eligibility.

    Stabilized percentages intentionally use every row in the season cohort. Eligibility is a
    later evaluation stage, so low-sample rows can inform the league shooting prior without being
    ranked or rated themselves.
    """
    missing = sorted(required_input_fields(metrics) - set(frame.columns))
    if missing:
        raise MetricPreparationError(
            f"Formula evaluation is missing required input columns: {', '.join(missing)}"
        )

    result = frame.reset_index(drop=True).copy()
    resolved: set[str] = set()
    resolving: set[str] = set()

    def materialize(name: str) -> None:
        if name in resolved:
            return
        if name in resolving:
            raise MetricPreparationError(f"Formula metric dependency cycle includes {name!r}")
        try:
            definition = metrics[name]
        except KeyError as error:
            raise MetricPreparationError(f"Formula references unknown metric {name!r}") from error

        resolving.add(name)
        kind = _value(definition, "kind")
        if kind == "input":
            field = str(_value(definition, "field"))
            result[name] = _numeric(result[field], field)
        else:
            inputs = tuple(str(item) for item in (_value(definition, "inputs") or ()))
            for input_name in inputs:
                materialize(input_name)

            if kind == "ratio":
                if len(inputs) != 2:
                    raise MetricPreparationError(
                        f"Ratio metric {name!r} must declare two inputs"
                    )
                result[name] = _validate_derived(
                    _ratio(result[inputs[0]], result[inputs[1]]), name
                )
            elif kind == "stabilizedPercentage":
                if len(inputs) != 2:
                    raise MetricPreparationError(
                        f"Stabilized percentage metric {name!r} must declare two inputs"
                    )
                if "season" not in metrics:
                    raise MetricPreparationError(
                        f"Stabilized percentage metric {name!r} requires a season metric"
                    )
                materialize("season")
                prior_attempts = float(_value(definition, "prior_attempts"))
                result[name] = _validate_derived(
                    _stabilized_percentage(
                        result[inputs[0]],
                        result[inputs[1]],
                        result["season"],
                        prior_attempts,
                    ),
                    name,
                )
            elif kind == "scheduledRatio":
                if len(inputs) != 2:
                    raise MetricPreparationError(
                        f"Scheduled ratio metric {name!r} must declare value and season inputs"
                    )
                schedule = _value(definition, "schedule")
                if not isinstance(schedule, Mapping):
                    raise MetricPreparationError(
                        f"Scheduled ratio metric {name!r} has no schedule"
                    )
                denominators = result[inputs[1]].map(
                    lambda season: _schedule_value(schedule, season)
                )
                unsupported = sorted(
                    {
                        str(season)
                        for season, denominator in zip(
                            result[inputs[1]], denominators, strict=False
                        )
                        if pd.notna(season) and denominator is None
                    }
                )
                if unsupported:
                    raise MetricPreparationError(
                        f"Scheduled ratio metric {name!r} has no schedule for seasons: "
                        f"{', '.join(unsupported)}"
                    )
                result[name] = _ratio(
                    result[inputs[0]], _numeric(denominators, f"{name} schedule")
                ).clip(lower=0.0, upper=1.0)
                result[name] = _validate_derived(result[name], name)
            else:
                raise MetricPreparationError(
                    f"Formula metric {name!r} uses unsupported kind {kind!r}"
                )

        resolving.remove(name)
        resolved.add(name)

    for metric_name in metrics:
        materialize(metric_name)
    return result
