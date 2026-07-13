"""Shared version 1 roster model constants."""

from __future__ import annotations

from typing import Final

RATING_FIELDS: Final[tuple[str, ...]] = (
    "insideScoring",
    "threePointShooting",
    "freeThrowShooting",
    "scoringVolume",
    "playmaking",
    "ballSecurity",
    "offensiveRebounding",
    "defensiveRebounding",
    "perimeterDefense",
    "interiorDefense",
    "stamina",
    "durability",
)

ALL_RATING_FIELDS: Final[tuple[str, ...]] = (*RATING_FIELDS, "overall", "potential")

TIER_ORDER: Final[tuple[str, ...]] = (
    "superstar",
    "all_star",
    "starter",
    "rotation",
    "fringe",
)
