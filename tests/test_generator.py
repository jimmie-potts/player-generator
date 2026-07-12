from __future__ import annotations

from copy import deepcopy

import pandas as pd

from player_generator.generator import generate_league
from player_generator.schema import RATING_FIELDS


def _small_config(default_config: dict) -> dict:
    config = deepcopy(default_config)
    generation = config["league_generation"]
    generation["team_count"] = 2
    generation["roster_size"] = 3
    generation["talent_targets"] = {
        "superstar": 1,
        "all_star": 1,
        "starter": 1,
        "rotation": 2,
        "fringe": 1,
    }
    generation["position_targets"] = {"guard": 2, "wing": 2, "big": 2}
    generation["roster_position_targets"] = {"guard": 1, "wing": 1, "big": 1}
    return config


def _reference() -> pd.DataFrame:
    rows = []
    tiers = ["superstar", "all_star", "starter", "rotation", "fringe"]
    groups = ["guard", "wing", "big"]
    for index, tier in enumerate(tiers):
        for group_index, group in enumerate(groups):
            overall = [94, 87, 80, 72, 62][index]
            row = {
                "sourcePlayerName": f"Reference {tier} {group}",
                "talentTier": tier,
                "positionGroup": group,
                "minutes": 1500 + group_index,
                "heightInches": 75 + group_index * 3,
                "weightPounds": 195 + group_index * 25,
                "overall": overall,
            }
            row.update({field: 60 + index + group_index for field in RATING_FIELDS})
            rows.append(row)
    return pd.DataFrame(rows)


def test_generation_is_deterministic_and_has_no_reference_names(default_config: dict) -> None:
    config = _small_config(default_config)
    reference = _reference()
    league_a, players_a = generate_league(reference, config, seed=42)
    league_b, players_b = generate_league(reference, config, seed=42)

    assert league_a["players"][0]["displayName"] == league_b["players"][0]["displayName"]
    assert players_a["overall"].tolist() == players_b["overall"].tolist()
    assert len(players_a) == 6
    assert not set(players_a["displayName"]).intersection(reference["sourcePlayerName"])
    assert all(len(team["roster"]) == 3 for team in league_a["teams"])
