from __future__ import annotations

import hashlib
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


def _formula_bytes(path: Path | None) -> bytes:
    if path is None:
        resource = files("player_attribute_engine").joinpath(_ACTIVE_FORMULA_RESOURCE)
        try:
            return resource.read_bytes()
        except OSError as error:
            raise FormulaContractError(
                f"Unable to read the active formula document: {error}"
            ) from error
    try:
        return path.read_bytes()
    except OSError as error:
        raise FormulaContractError(
            f"Unable to read formula document {path}: {error}"
        ) from error


def formula_content_hash(path: Path | None = None) -> str:
    """Return the SHA-256 hash of the exact formula document bytes."""
    return hashlib.sha256(_formula_bytes(path)).hexdigest()


def load_formula_snapshot(path: Path | None = None) -> tuple[FormulaDocument, str]:
    """Parse and hash one immutable read of a formula document."""
    load_formula_contract(FORMULA_SCHEMA_VERSION)
    content = _formula_bytes(path)
    try:
        payload = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        if path is None:
            raise FormulaContractError(
                f"Unable to load the active formula document: {error}"
            ) from error
        raise FormulaContractError(
            f"Unable to load formula document {path}: {error}"
        ) from error

    document = parse_formula_document(payload)
    if path is None and document.formula_version != ACTIVE_FORMULA_VERSION:
        raise FormulaContractError(
            "Active formula resource version mismatch: "
            f"{document.formula_version!r} != {ACTIVE_FORMULA_VERSION!r}"
        )
    return document, hashlib.sha256(content).hexdigest()


def load_formula(path: Path | None = None) -> FormulaDocument:
    """Load and validate the active formula document or an explicit JSON proposal."""
    return load_formula_snapshot(path)[0]


__all__ = [
    "ACTIVE_FORMULA_VERSION",
    "FORMULA_SCHEMA_VERSION",
    "formula_content_hash",
    "load_formula",
    "load_formula_snapshot",
]
