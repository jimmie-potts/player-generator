from __future__ import annotations

import hashlib
import json
from importlib.resources import files
from pathlib import Path

import pytest
from player_attribute_engine import (
    ACTIVE_FORMULA_VERSION,
    FormulaContractError,
    formula_content_hash,
    load_formula,
    load_formula_payload_snapshot,
    load_formula_snapshot,
)
from player_data_contracts import REFERENCE_CONTRACT_VERSION


def test_active_formula_document_is_packaged_and_complete() -> None:
    formula = load_formula()

    assert formula.formula_version == ACTIVE_FORMULA_VERSION == "1.0.0"
    assert REFERENCE_CONTRACT_VERSION == 1
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


def test_formula_content_hash_pins_exact_document_bytes(tmp_path: Path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first.write_text('{"formulaVersion":"1"}\n', encoding="utf-8")
    second.write_text('{"formulaVersion": "1"}\n', encoding="utf-8")

    assert len(formula_content_hash()) == 64
    assert formula_content_hash(first) == formula_content_hash(first)
    assert formula_content_hash(first) != formula_content_hash(second)


def test_formula_snapshot_hashes_the_same_bytes_it_parses(tmp_path: Path) -> None:
    active = load_formula()
    path = tmp_path / "formula.json"
    path.write_bytes(
        files("player_attribute_engine")
        .joinpath("formulas/player-attributes-v1.json")
        .read_bytes()
    )

    snapshot, digest = load_formula_snapshot(path)
    path.write_text(json.dumps({"changed": True}) + "\n", encoding="utf-8")

    assert snapshot == active
    assert digest != formula_content_hash(path)


def test_formula_payload_snapshot_returns_raw_json_and_the_same_parsed_bytes(
    tmp_path: Path,
) -> None:
    path = tmp_path / "formula.json"
    content = (
        files("player_attribute_engine")
        .joinpath("formulas/player-attributes-v1.json")
        .read_bytes()
    )
    path.write_bytes(content)

    payload, document, digest = load_formula_payload_snapshot(path)
    assert payload["formulaVersion"] == ACTIVE_FORMULA_VERSION
    payload["formulaVersion"] = "modified-after-load"
    path.write_text(json.dumps({"changed": True}) + "\n", encoding="utf-8")

    assert document == load_formula()
    assert document.formula_version == ACTIVE_FORMULA_VERSION
    assert digest == hashlib.sha256(content).hexdigest()
    assert digest != formula_content_hash(path)
