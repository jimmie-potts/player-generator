from __future__ import annotations

import numpy as np
import pandas as pd


def safe_divide(numerator: pd.Series, denominator: pd.Series, default: float = 0.0) -> pd.Series:
    denominator = denominator.astype(float)
    result = numerator.astype(float).div(denominator.where(denominator != 0))
    return result.replace([np.inf, -np.inf], np.nan).fillna(default)
