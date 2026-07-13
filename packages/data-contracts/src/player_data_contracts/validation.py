from __future__ import annotations

from typing import Any


class ContractValidationError(ValueError):
    """Raised when a payload does not satisfy a versioned data contract."""


def validate_roster_payload(payload: dict[str, Any]) -> None:
    """Validate the required top-level fields of the existing roster v1 contract."""
    expected_types: dict[str, type] = {
        "schemaVersion": int,
        "generationSeed": int,
        "league": dict,
        "players": list,
        "teams": list,
    }
    missing = [field for field in expected_types if field not in payload]
    if missing:
        raise ContractValidationError(
            f"Roster contract v1 is missing required fields: {', '.join(missing)}"
        )
    if payload["schemaVersion"] != 1:
        raise ContractValidationError(
            f"Unsupported roster contract version: {payload['schemaVersion']}"
        )
    wrong_types = [
        field
        for field, expected in expected_types.items()
        if not isinstance(payload[field], expected)
    ]
    if wrong_types:
        raise ContractValidationError(
            f"Roster contract v1 has invalid field types: {', '.join(wrong_types)}"
        )
    if "generatedAt" in payload and not isinstance(payload["generatedAt"], str):
        raise ContractValidationError("Roster contract v1 has invalid field type: generatedAt")

    league = payload["league"]
    league_fields = {
        "name": str,
        "season": str,
        "teamCount": int,
        "playerCount": int,
    }
    invalid_league_fields = [
        field
        for field, expected in league_fields.items()
        if field not in league or not isinstance(league[field], expected)
    ]
    if invalid_league_fields:
        raise ContractValidationError(
            "Roster contract v1 has invalid league fields: "
            f"{', '.join(invalid_league_fields)}"
        )

    players = payload["players"]
    teams = payload["teams"]
    if league["playerCount"] != len(players):
        raise ContractValidationError(
            "Roster contract v1 playerCount does not match players: "
            f"{league['playerCount']} != {len(players)}"
        )
    if league["teamCount"] != len(teams):
        raise ContractValidationError(
            "Roster contract v1 teamCount does not match teams: "
            f"{league['teamCount']} != {len(teams)}"
        )

    invalid_player_ids = [
        index
        for index, player in enumerate(players)
        if not isinstance(player, dict) or not isinstance(player.get("id"), str)
    ]
    if invalid_player_ids:
        raise ContractValidationError(
            "Roster contract v1 has invalid player IDs at indexes: "
            f"{', '.join(str(index) for index in invalid_player_ids)}"
        )
    player_ids = {player["id"] for player in players}

    invalid_team_rosters = [
        index
        for index, team in enumerate(teams)
        if not isinstance(team, dict)
        or not isinstance(team.get("roster"), list)
        or any(not isinstance(player_id, str) for player_id in team["roster"])
    ]
    if invalid_team_rosters:
        raise ContractValidationError(
            "Roster contract v1 has invalid team rosters at indexes: "
            f"{', '.join(str(index) for index in invalid_team_rosters)}"
        )

    unknown_roster_ids = sorted(
        {
            player_id
            for team in teams
            for player_id in team["roster"]
            if player_id not in player_ids
        }
    )
    if unknown_roster_ids:
        raise ContractValidationError(
            "Roster contract v1 team rosters reference unknown player IDs: "
            f"{', '.join(unknown_roster_ids)}"
        )
