from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from importlib.resources import files
from pathlib import Path
from typing import Any, Final

from player_data_contracts.csv_contract import (
    contract_files,
    validate_csv_package,
    validate_csv_tables,
)
from player_data_contracts.validation import ContractValidationError

REFERENCE_CONTRACT_VERSION: Final = 1

_REFERENCE_SCHEMA_NAME = "schemas/reference-v1.schema.json"
_CONTRACT_NAME = "Reference"


def load_reference_contract(
    version: int = REFERENCE_CONTRACT_VERSION,
) -> dict[str, Any]:
    """Load the machine-readable normalized reference CSV contract."""
    if version != REFERENCE_CONTRACT_VERSION:
        raise ContractValidationError(f"Unsupported reference contract version: {version}")

    resource = files("player_data_contracts").joinpath(_REFERENCE_SCHEMA_NAME)
    try:
        with resource.open("r", encoding="utf-8") as handle:
            contract = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        raise ContractValidationError(
            f"Unable to load reference contract version {version}: {error}"
        ) from error
    if not isinstance(contract, dict) or contract.get("contractVersion") != version:
        raise ContractValidationError(
            f"Reference contract resource does not declare version {version}"
        )
    contract_files(
        contract,
        contract_name=_CONTRACT_NAME,
        contract_version=REFERENCE_CONTRACT_VERSION,
    )
    return contract


def validate_reference_tables(
    tables: Mapping[str, Sequence[Mapping[str, object]]],
    *,
    contract: Mapping[str, Any] | None = None,
) -> None:
    """Validate in-memory rows for all normalized reference CSV tables."""
    active_contract = contract if contract is not None else load_reference_contract()
    validate_csv_tables(
        tables,
        contract=active_contract,
        contract_name=_CONTRACT_NAME,
        contract_version=REFERENCE_CONTRACT_VERSION,
    )


def validate_reference_package(
    package_dir: str | Path,
    *,
    contract: Mapping[str, Any] | None = None,
) -> None:
    """Read and validate the six normalized CSVs in a reference package directory."""
    active_contract = contract if contract is not None else load_reference_contract()
    validate_csv_package(
        package_dir,
        contract=active_contract,
        contract_name=_CONTRACT_NAME,
        contract_version=REFERENCE_CONTRACT_VERSION,
    )
