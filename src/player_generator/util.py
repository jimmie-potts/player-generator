from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def parse_minutes(value: object) -> float:
    """Convert NBA-style MM:SS strings or numeric values to decimal minutes."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return 0.0
    if isinstance(value, (int, float)):
        return max(0.0, float(value))

    text = str(value).strip()
    if not text:
        return 0.0
    if ":" in text:
        minutes, seconds = text.split(":", 1)
        try:
            return max(0.0, float(minutes) + float(seconds) / 60.0)
        except ValueError:
            return 0.0
    try:
        return max(0.0, float(text))
    except ValueError:
        return 0.0


def safe_divide(numerator: pd.Series, denominator: pd.Series, default: float = 0.0) -> pd.Series:
    denominator = denominator.astype(float)
    result = numerator.astype(float).div(denominator.where(denominator != 0))
    return result.replace([np.inf, -np.inf], np.nan).fillna(default)


def clamp_int(value: float, minimum: int = 25, maximum: int = 99) -> int:
    return int(max(minimum, min(maximum, round(float(value)))))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


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
