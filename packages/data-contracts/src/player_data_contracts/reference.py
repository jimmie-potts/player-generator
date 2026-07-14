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

REFERENCE_CONTRACT_VERSION: Final = 2
SUPPORTED_REFERENCE_CONTRACT_VERSIONS: Final = (1, 2)

_REFERENCE_SCHEMA_NAMES: Final = {
    1: "schemas/reference-v1.schema.json",
    2: "schemas/reference-v2.schema.json",
}
_CONTRACT_NAME = "Reference"


def load_reference_contract(
    version: int = REFERENCE_CONTRACT_VERSION,
) -> dict[str, Any]:
    """Load the machine-readable normalized reference CSV contract."""
    if (
        isinstance(version, bool)
        or not isinstance(version, int)
        or version not in SUPPORTED_REFERENCE_CONTRACT_VERSIONS
    ):
        raise ContractValidationError(f"Unsupported reference contract version: {version}")

    resource = files("player_data_contracts").joinpath(_REFERENCE_SCHEMA_NAMES[version])
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
        contract_version=version,
    )
    return contract


def _declared_contract_version(contract: Mapping[str, Any]) -> int:
    version = contract.get("contractVersion")
    if isinstance(version, bool) or not isinstance(version, int):
        raise ContractValidationError(f"Unsupported reference contract version: {version!r}")
    if version not in SUPPORTED_REFERENCE_CONTRACT_VERSIONS:
        raise ContractValidationError(f"Unsupported reference contract version: {version}")
    return version


def validate_reference_tables(
    tables: Mapping[str, Sequence[Mapping[str, object]]],
    *,
    contract: Mapping[str, Any] | None = None,
) -> None:
    """Validate in-memory rows for all normalized reference CSV tables."""
    active_contract = contract if contract is not None else load_reference_contract()
    contract_version = _declared_contract_version(active_contract)
    validate_csv_tables(
        tables,
        contract=active_contract,
        contract_name=_CONTRACT_NAME,
        contract_version=contract_version,
    )


def validate_reference_package(
    package_dir: str | Path,
    *,
    contract: Mapping[str, Any] | None = None,
) -> None:
    """Read and validate normalized CSVs in a reference package directory."""
    active_contract = contract if contract is not None else load_reference_contract()
    contract_version = _declared_contract_version(active_contract)
    validate_csv_package(
        package_dir,
        contract=active_contract,
        contract_name=_CONTRACT_NAME,
        contract_version=contract_version,
    )
