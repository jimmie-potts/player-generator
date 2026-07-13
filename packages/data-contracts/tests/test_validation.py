from __future__ import annotations

from importlib.resources import files

import pytest
from player_data_contracts.validation import ContractValidationError, validate_roster_payload


def _payload() -> dict:
    return {
        "schemaVersion": 1,
        "generatedAt": "2026-07-12",
        "generationSeed": 42,
        "league": {
            "name": "Test League",
            "season": "2026-27",
            "teamCount": 0,
            "playerCount": 0,
        },
        "teams": [],
        "players": [],
    }


def test_roster_v1_validation_accepts_required_shape() -> None:
    validate_roster_payload(_payload())


def test_roster_v1_validation_rejects_unsupported_version() -> None:
    payload = _payload()
    payload["schemaVersion"] = 2
    with pytest.raises(ContractValidationError, match="Unsupported"):
        validate_roster_payload(payload)


def test_roster_v1_validation_rejects_missing_fields() -> None:
    payload = _payload()
    payload.pop("players")
    with pytest.raises(ContractValidationError, match="missing"):
        validate_roster_payload(payload)


def test_roster_v1_schema_is_packaged() -> None:
    schema = files("player_data_contracts").joinpath("schemas/roster-v1.schema.json")
    assert schema.is_file()
