"""Versioned data contracts shared by the player data applications."""

from player_data_contracts.formula import FORMULA_CONTRACT_VERSION, load_formula_contract
from player_data_contracts.models import ALL_RATING_FIELDS, RATING_FIELDS, TIER_ORDER
from player_data_contracts.reference import (
    REFERENCE_CONTRACT_VERSION,
    load_reference_contract,
    validate_reference_package,
    validate_reference_tables,
)
from player_data_contracts.validation import ContractValidationError, validate_roster_payload

__all__ = [
    "ALL_RATING_FIELDS",
    "ContractValidationError",
    "FORMULA_CONTRACT_VERSION",
    "RATING_FIELDS",
    "REFERENCE_CONTRACT_VERSION",
    "TIER_ORDER",
    "load_formula_contract",
    "load_reference_contract",
    "validate_reference_package",
    "validate_reference_tables",
    "validate_roster_payload",
]

__version__ = "0.2.0"
