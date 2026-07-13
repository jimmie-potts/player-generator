from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd


def stable_rank_percentile(series: pd.Series, higher_is_better: bool = True) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    filled = numeric.fillna(numeric.median() if numeric.notna().any() else 0.0)
    return filled.rank(method="average", pct=True, ascending=higher_is_better)


def interpolate_rating(
    percentile: pd.Series | np.ndarray | float,
    percentile_anchors: Iterable[float],
    rating_anchors: Iterable[float],
) -> np.ndarray:
    values = np.asarray(percentile, dtype=float)
    return np.interp(
        np.clip(values, 0.0, 1.0),
        np.asarray(list(percentile_anchors), dtype=float),
        np.asarray(list(rating_anchors), dtype=float),
    )
