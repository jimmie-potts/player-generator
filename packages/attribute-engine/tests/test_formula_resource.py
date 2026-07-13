from __future__ import annotations

import json
from pathlib import Path

import pytest
from player_attribute_engine import (
    ACTIVE_FORMULA_VERSION,
    FormulaContractError,
    load_formula,
)


def test_active_formula_document_is_packaged_and_complete() -> None:
    formula = load_formula()

    assert formula.formula_version == ACTIVE_FORMULA_VERSION == "1.0.0"
    assert formula.reference_contract_version == 1
    assert [attribute.name for attribute in formula.attributes] == [
        "insideScoring",
        "threePointShooting",
        "freeThrowShooting",
        "scoringVolume",
        "playmaking",
        "ballSecurity",
        "offensiveRebounding",
        "defensiveRebounding",
        "perimeterDefense",
        "interiorDefense",
        "stamina",
        "durability",
        "overall",
    ]
    assert formula.output_fields == (
        "playerId",
        "insideScoring",
        "threePointShooting",
        "freeThrowShooting",
        "scoringVolume",
        "playmaking",
        "ballSecurity",
        "offensiveRebounding",
        "defensiveRebounding",
        "perimeterDefense",
        "interiorDefense",
        "stamina",
        "durability",
        "overall",
        "impactPercentile",
        "talentTier",
        "formulaVersion",
    )


def test_forward_formula_document_is_rejected_before_use(tmp_path: Path) -> None:
    active_path = tmp_path / "formula-v1.json"
    active_path.write_text(
        json.dumps(
            {
                "schemaVersion": 2,
                "formulaVersion": "2.0.0",
                "referenceContractVersion": 1,
                "outputFields": [],
                "rules": {},
                "metrics": {},
                "cohorts": {},
                "eligibilityRules": {},
                "ratingScales": {},
                "attributes": [],
                "talentTiers": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(FormulaContractError, match="Unsupported formula schema version 2"):
        load_formula(active_path)
