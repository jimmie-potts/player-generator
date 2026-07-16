from __future__ import annotations

import json
from collections.abc import Mapping
from importlib.resources import files
from typing import Any, Final

from player_data_contracts.validation import ContractValidationError, safe_repr

FORMULA_CONTRACT_VERSION: Final = 1

_FORMULA_SCHEMA_NAME = "schemas/formula-v1.schema.json"
_REQUIRED_DOCUMENT_FIELDS: Final = (
    "schemaVersion",
    "formulaVersion",
    "referenceContractVersion",
    "outputFields",
    "rules",
    "metrics",
    "cohorts",
    "eligibilityRules",
    "ratingScales",
    "attributes",
    "talentTiers",
)


def load_formula_contract(
    version: int = FORMULA_CONTRACT_VERSION,
) -> dict[str, Any]:
    """Load the machine-readable structural contract for formula documents."""
    if type(version) is not int or version != FORMULA_CONTRACT_VERSION:
        raise ContractValidationError(
            f"Unsupported formula contract version: {safe_repr(version)}"
        )

    resource = files("player_data_contracts").joinpath(_FORMULA_SCHEMA_NAME)
    try:
        with resource.open("r", encoding="utf-8") as handle:
            contract = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        raise ContractValidationError(
            f"Unable to load formula contract version {version}: {error}"
        ) from error

    _validate_formula_contract_resource(contract, version)
    return contract


def _validate_formula_contract_resource(contract: object, version: int) -> None:
    if not isinstance(contract, Mapping) or contract.get("contractVersion") != version:
        raise ContractValidationError(
            f"Formula contract resource does not declare version {version}"
        )

    properties = contract.get("properties")
    schema_version = properties.get("schemaVersion") if isinstance(properties, Mapping) else None
    if not isinstance(schema_version, Mapping) or schema_version.get("const") != version:
        raise ContractValidationError(
            f"Formula contract resource does not require schemaVersion {version}"
        )

    required = contract.get("required")
    if not isinstance(required, list):
        raise ContractValidationError(
            "Formula contract resource has no required document fields"
        )
    missing = [field for field in _REQUIRED_DOCUMENT_FIELDS if field not in required]
    if missing:
        raise ContractValidationError(
            "Formula contract resource is missing required document fields: "
            f"{', '.join(missing)}"
        )
