from __future__ import annotations

from dataclasses import dataclass
from typing import Final

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
