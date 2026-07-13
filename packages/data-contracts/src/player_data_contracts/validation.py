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
