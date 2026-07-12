from __future__ import annotations

from dataclasses import dataclass
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

POSITION_GROUPS: Final[tuple[str, ...]] = ("guard", "wing", "big")


@dataclass(frozen=True)
class TeamDefinition:
    team_id: str
    city: str
    nickname: str
    abbreviation: str
    conference: str

    @property
    def full_name(self) -> str:
        return f"{self.city} {self.nickname}"
