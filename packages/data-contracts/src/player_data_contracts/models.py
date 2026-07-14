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
