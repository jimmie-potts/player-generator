from __future__ import annotations

import pandas as pd

from player_generator.comparison import compare_rosters
from player_generator.schema import RATING_FIELDS


def test_comparison_detects_name_collision() -> None:
    base = {
        "positionGroup": "guard",
        "talentTier": "starter",
        "overall": 80,
        **{field: 70 for field in RATING_FIELDS},
    }
    reference = pd.DataFrame([{**base, "sourcePlayerName": "Named Player"}])
    generated = pd.DataFrame([{**base, "displayName": "Named Player"}])
    report, table = compare_rosters(reference, generated)
    assert report["identityChecks"]["generatedNameCollisionsWithReference"] == 1
    assert report["identityChecks"]["exactFullRatingVectorMatches"] == 1
    assert len(table) == len(RATING_FIELDS) + 1
