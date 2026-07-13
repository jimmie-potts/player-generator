from __future__ import annotations

import pandas as pd
from player_data_contracts.models import RATING_FIELDS
from roster_generator.comparison import compare_rosters


def test_comparison_detects_name_collision() -> None:
    base = {
        "positionGroup": "guard",
        "talentTier": "starter",
        "overall": 80,
        **{field: 70 for field in RATING_FIELDS},
    }
    reference = pd.DataFrame([{**base, "sourcePlayerName": "Named Player"}])
    roster = pd.DataFrame([{**base, "displayName": "Named Player"}])
    report, table = compare_rosters(reference, roster)
    assert report["identityChecks"]["rosterNameCollisionsWithReference"] == 1
    assert report["identityChecks"]["exactFullRatingVectorMatches"] == 1
    assert len(table) == len(RATING_FIELDS) + 1
