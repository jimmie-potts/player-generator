from __future__ import annotations

import json
from pathlib import Path

import player_data_contracts.formula as formula_module
import pytest
from player_data_contracts import (
    FORMULA_CONTRACT_VERSION,
    ContractValidationError,
    load_formula_contract,
)


def test_formula_v1_contract_loads_required_document_shape() -> None:
    contract = load_formula_contract()

    assert contract["contractVersion"] == FORMULA_CONTRACT_VERSION == 1
    assert contract["properties"]["schemaVersion"]["const"] == 1
    assert contract["properties"]["referenceContractVersion"]["const"] == 1
    assert contract["required"] == [
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
    ]
    assert contract["properties"]["rules"]["properties"] == {
        "nullHandling": {"const": "exclude"},
        "tieMethod": {"const": "average"},
        "percentileMethod": {"const": "rankPct"},
        "ratingRounding": {"const": "halfEven"},
    }
    assert set(contract["$defs"]["metric"]["properties"]) == {
        "kind",
        "field",
        "inputs",
        "priorAttempts",
        "schedule",
    }
    assert contract["$defs"]["metric"]["properties"]["schedule"] == {
        "type": "object",
        "minProperties": 1,
        "propertyNames": {"pattern": "^[1-9][0-9]{3}$"},
        "additionalProperties": {"type": "integer", "minimum": 1},
    }
    assert "rerankComposite" in contract["$defs"]["attribute"]["required"]
    assert contract["$defs"]["attribute"]["properties"]["percentileOutput"] == {
        "type": "string",
        "minLength": 1,
    }


def test_formula_contract_rejects_forward_version() -> None:
    with pytest.raises(
        ContractValidationError,
        match="Unsupported formula contract version: 2",
    ):
        load_formula_contract(version=2)


def test_formula_contract_rejects_packaged_resource_version_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    schema_dir = tmp_path / "schemas"
    schema_dir.mkdir()
    contract = load_formula_contract()
    contract["properties"]["schemaVersion"]["const"] = 2
    (schema_dir / "formula-v1.schema.json").write_text(
        json.dumps(contract),
        encoding="utf-8",
    )
    monkeypatch.setattr(formula_module, "files", lambda package: tmp_path)

    with pytest.raises(
        ContractValidationError,
        match="does not require schemaVersion 1",
    ):
        formula_module.load_formula_contract()
