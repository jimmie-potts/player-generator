from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path
from typing import Final

from player_data_contracts import load_formula_contract

from player_attribute_engine.contract import (
    FormulaContractError,
    FormulaDocument,
    parse_formula_document,
)

FORMULA_SCHEMA_VERSION: Final = 1
ACTIVE_FORMULA_VERSION: Final = "1.0.0"
_ACTIVE_FORMULA_RESOURCE: Final = "formulas/player-attributes-v1.json"


def load_formula(path: Path | None = None) -> FormulaDocument:
    """Load and validate the active formula document or an explicit JSON proposal."""
    load_formula_contract(FORMULA_SCHEMA_VERSION)
    if path is None:
        resource = files("player_attribute_engine").joinpath(_ACTIVE_FORMULA_RESOURCE)
        try:
            with resource.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError) as error:
            raise FormulaContractError(
                f"Unable to load the active formula document: {error}"
            ) from error
    else:
        try:
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError) as error:
            raise FormulaContractError(
                f"Unable to load formula document {path}: {error}"
            ) from error

    document = parse_formula_document(payload)
    if path is None and document.formula_version != ACTIVE_FORMULA_VERSION:
        raise FormulaContractError(
            "Active formula resource version mismatch: "
            f"{document.formula_version!r} != {ACTIVE_FORMULA_VERSION!r}"
        )
    return document


__all__ = [
    "ACTIVE_FORMULA_VERSION",
    "FORMULA_SCHEMA_VERSION",
    "load_formula",
]
