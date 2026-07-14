"""Versioned data contracts shared by the player data applications."""

from player_data_contracts.formula import FORMULA_CONTRACT_VERSION, load_formula_contract
from player_data_contracts.models import RATING_FIELDS
from player_data_contracts.package import content_hash
from player_data_contracts.reference import (
    REFERENCE_CONTRACT_VERSION,
    SUPPORTED_REFERENCE_CONTRACT_VERSIONS,
    load_reference_contract,
    validate_reference_package,
    validate_reference_tables,
)
from player_data_contracts.reference_package import (
    LoadedReferencePackageTables,
    ReferencePackageIntegrityError,
    load_reference_package_tables,
)
from player_data_contracts.roster import (
    ROSTER_CONTRACT_VERSION,
    load_roster_contract,
    validate_roster_package,
    validate_roster_tables,
)
from player_data_contracts.validation import ContractValidationError

__all__ = [
    "ContractValidationError",
    "FORMULA_CONTRACT_VERSION",
    "LoadedReferencePackageTables",
    "RATING_FIELDS",
    "REFERENCE_CONTRACT_VERSION",
    "SUPPORTED_REFERENCE_CONTRACT_VERSIONS",
    "ROSTER_CONTRACT_VERSION",
    "ReferencePackageIntegrityError",
    "content_hash",
    "load_formula_contract",
    "load_reference_contract",
    "load_reference_package_tables",
    "load_roster_contract",
    "validate_reference_package",
    "validate_reference_tables",
    "validate_roster_package",
    "validate_roster_tables",
]

__version__ = "0.2.0"
