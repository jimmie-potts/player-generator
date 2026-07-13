from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

import numpy as np
import pandas as pd
from player_attribute_engine import evaluate_player_attributes

from roster_generator.reference_package import LoadedReferencePackage

_SELECTION_KEYS = {
    "seasons",
    "season_weights",
    "minimum_games",
    "minimum_minutes",
    "roster_size",
    "minutes_weight_exponent",
    "with_replacement",
}


class SelectionError(ValueError):
    """Raised when template eligibility or sampling cannot be completed."""


def _integer(value: object, field: str, *, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SelectionError(f"selection.{field} must be an integer.")
    if value < minimum:
        raise SelectionError(f"selection.{field} must be at least {minimum}.")
    return value


def _number(value: object, field: str, *, minimum: float, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SelectionError(f"selection.{field} must be a finite number.")
    result = float(value)
    if not math.isfinite(result):
        raise SelectionError(f"selection.{field} must be a finite number.")
    if positive and result <= minimum:
        raise SelectionError(f"selection.{field} must be greater than {minimum:g}.")
    if not positive and result < minimum:
        raise SelectionError(f"selection.{field} must be at least {minimum:g}.")
    return result


def _season_key(value: object, field: str) -> int:
    if isinstance(value, bool):
        raise SelectionError(f"selection.{field} must identify a positive integer season.")
    if isinstance(value, int):
        season = value
    elif isinstance(value, str) and value.isdigit():
        season = int(value)
    else:
        raise SelectionError(f"selection.{field} must identify a positive integer season.")
    if season < 1:
        raise SelectionError(f"selection.{field} must identify a positive integer season.")
    return season


@dataclass(frozen=True)
class SelectionSettings:
    """Validated, immutable controls for reference template sampling."""

    seasons: tuple[int, ...]
    season_weights: Mapping[int, float]
    minimum_games: int
    minimum_minutes: float
    roster_size: int
    minutes_weight_exponent: float
    with_replacement: bool

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, object]) -> SelectionSettings:
        """Parse the exact ``selection`` configuration mapping."""
        if not isinstance(mapping, Mapping):
            raise SelectionError("selection must be an object.")
        missing = sorted(_SELECTION_KEYS - set(mapping))
        unknown = sorted(set(mapping) - _SELECTION_KEYS)
        if missing:
            raise SelectionError(f"selection is missing keys: {', '.join(missing)}.")
        if unknown:
            raise SelectionError(f"selection has unknown keys: {', '.join(unknown)}.")

        raw_seasons = mapping["seasons"]
        if (
            isinstance(raw_seasons, (str, bytes))
            or not isinstance(raw_seasons, Sequence)
            or not raw_seasons
        ):
            raise SelectionError("selection.seasons must be a non-empty array.")
        seasons = tuple(
            _season_key(value, f"seasons[{index}]") for index, value in enumerate(raw_seasons)
        )
        if len(seasons) != len(set(seasons)):
            raise SelectionError("selection.seasons must not contain duplicates.")

        raw_weights = mapping["season_weights"]
        if not isinstance(raw_weights, Mapping):
            raise SelectionError("selection.season_weights must be an object.")
        weights: dict[int, float] = {}
        for raw_season, raw_weight in raw_weights.items():
            season = _season_key(raw_season, f"season_weights[{raw_season!r}]")
            if season in weights:
                raise SelectionError(
                    f"selection.season_weights contains duplicate season {season}."
                )
            weights[season] = _number(
                raw_weight,
                f"season_weights[{season}]",
                minimum=0.0,
                positive=True,
            )
        missing_weights = sorted(set(seasons) - set(weights))
        extra_weights = sorted(set(weights) - set(seasons))
        if missing_weights or extra_weights:
            details: list[str] = []
            if missing_weights:
                details.append(f"missing {', '.join(map(str, missing_weights))}")
            if extra_weights:
                details.append(f"unexpected {', '.join(map(str, extra_weights))}")
            raise SelectionError(
                "selection.season_weights must cover exactly selection.seasons: "
                + "; ".join(details)
                + "."
            )

        with_replacement = mapping["with_replacement"]
        if not isinstance(with_replacement, bool):
            raise SelectionError("selection.with_replacement must be a boolean.")
        return cls(
            seasons=seasons,
            season_weights=MappingProxyType(weights),
            minimum_games=_integer(mapping["minimum_games"], "minimum_games", minimum=0),
            minimum_minutes=_number(mapping["minimum_minutes"], "minimum_minutes", minimum=0.0),
            roster_size=_integer(mapping["roster_size"], "roster_size", minimum=1),
            minutes_weight_exponent=_number(
                mapping["minutes_weight_exponent"],
                "minutes_weight_exponent",
                minimum=0.0,
            ),
            with_replacement=with_replacement,
        )


def _formula_output_fields(formula: object) -> tuple[str, ...]:
    if isinstance(formula, Mapping):
        raw = formula.get("output_fields", formula.get("outputFields"))
    else:
        raw = getattr(formula, "output_fields", None)
    if isinstance(raw, (str, bytes)) or not isinstance(raw, Sequence) or not raw:
        raise SelectionError("Formula is missing a valid ordered output_fields declaration.")
    fields = tuple(str(field) for field in raw)
    if any(not field for field in fields):
        raise SelectionError("Formula output_fields contains an empty field name.")
    return fields


def eligible_candidates(
    package: LoadedReferencePackage,
    formula: object,
    settings: SelectionSettings,
) -> pd.DataFrame:
    """Evaluate complete season cohorts, then apply configured eligibility filters."""
    output_fields = _formula_output_fields(formula)
    season_batches: list[pd.DataFrame] = []
    for season in settings.seasons:
        cohort = package.frame.loc[package.frame["season"] == season].copy().reset_index(drop=True)
        if cohort.empty:
            continue

        evaluation = evaluate_player_attributes(cohort, formula)
        outputs = pd.DataFrame(evaluation.rows, columns=output_fields)
        if len(outputs) != len(cohort):
            raise SelectionError(
                f"Formula evaluation for season {season} returned {len(outputs)} rows; "
                f"expected {len(cohort)}."
            )
        overlapping = (set(output_fields) & set(cohort.columns)) - {"playerId"}
        if overlapping:
            raise SelectionError(
                "Formula output fields overlap reference input fields: "
                + ", ".join(sorted(overlapping))
                + "."
            )
        output_ids = tuple(str(value) for value in outputs.get("playerId", ()))
        cohort_ids = tuple(str(value) for value in cohort["playerId"])
        if "playerId" not in outputs or output_ids != cohort_ids:
            raise SelectionError(
                f"Formula evaluation for season {season} changed playerId row ordering."
            )

        complete = outputs[list(output_fields)].notna().all(axis=1)
        games_eligible = (cohort["games"] >= settings.minimum_games).fillna(False)
        minutes_eligible = (cohort["minutes"] >= settings.minimum_minutes).fillna(False)
        eligible = complete & games_eligible & minutes_eligible
        if not eligible.any():
            continue
        rows = pd.concat(
            [
                cohort.loc[eligible].reset_index(drop=True),
                outputs.loc[
                    eligible, [field for field in output_fields if field != "playerId"]
                ].reset_index(drop=True),
            ],
            axis=1,
        )
        rows["recencyWeight"] = settings.season_weights[season]
        season_batches.append(rows)

    if not season_batches:
        seasons = ", ".join(str(season) for season in settings.seasons)
        raise SelectionError(
            "No eligible reference templates remain after formula completeness and configured "
            f"games/minutes filters for seasons: {seasons}."
        )
    return pd.concat(season_batches, ignore_index=True)


def select_templates(
    candidates: pd.DataFrame,
    settings: SelectionSettings,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Select reference rows deterministically with recency and minutes weighting."""
    if candidates.empty:
        raise SelectionError("Cannot select templates from an empty eligible population.")
    if not settings.with_replacement and len(candidates) < settings.roster_size:
        raise SelectionError(
            "Eligible reference population is too small for sampling without replacement: "
            f"need {settings.roster_size}, found {len(candidates)}."
        )
    missing = [field for field in ("recencyWeight", "minutes") if field not in candidates]
    if missing:
        raise SelectionError(
            "Eligible reference candidates are missing selection fields: "
            + ", ".join(missing)
            + "."
        )

    recency = pd.to_numeric(candidates["recencyWeight"], errors="coerce").to_numpy(
        dtype=float, na_value=np.nan
    )
    minutes = pd.to_numeric(candidates["minutes"], errors="coerce").to_numpy(
        dtype=float, na_value=np.nan
    )
    weights = recency * np.power(minutes, settings.minutes_weight_exponent)
    if np.any(~np.isfinite(weights)) or np.any(weights < 0):
        raise SelectionError("Eligible reference candidates produced invalid selection weights.")
    total = float(weights.sum())
    if not math.isfinite(total) or total <= 0:
        raise SelectionError(
            "Eligible reference candidates must produce a positive total selection weight."
        )
    positive_count = int(np.count_nonzero(weights > 0))
    if not settings.with_replacement and positive_count < settings.roster_size:
        raise SelectionError(
            "Eligible reference population with positive selection weight is too small for "
            f"sampling without replacement: need {settings.roster_size}, "
            f"found {positive_count}."
        )
    probabilities = weights / total
    positions = rng.choice(
        len(candidates),
        size=settings.roster_size,
        replace=settings.with_replacement,
        p=probabilities,
    )
    return candidates.iloc[np.asarray(positions, dtype=int)].copy().reset_index(drop=True)


__all__ = [
    "SelectionError",
    "SelectionSettings",
    "eligible_candidates",
    "select_templates",
]
