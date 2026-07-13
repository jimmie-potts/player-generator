from __future__ import annotations

import math

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
