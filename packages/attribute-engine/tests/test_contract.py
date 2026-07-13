from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
from player_attribute_engine.contract import (
    FormulaContractError,
    FormulaDocument,
    parse_formula_document,
)


def _document() -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "formulaVersion": "1.0.0",
        "referenceContractVersion": 1,
        "outputFields": [
            "playerId",
            "insideScoring",
            "overall",
            "impactPercentile",
            "talentTier",
            "formulaVersion",
        ],
        "rules": {
            "nullHandling": "exclude",
            "percentileMethod": "rankPct",
            "tieMethod": "average",
            "ratingRounding": "halfEven",
        },
        "metrics": {
            "season": {"kind": "input", "field": "season"},
            "games": {"kind": "input", "field": "games"},
            "minutes": {"kind": "input", "field": "minutes"},
            "made": {"kind": "input", "field": "twoPointersMade"},
            "attempted": {"kind": "input", "field": "twoPointersAttempted"},
            "adjustedPercentage": {
                "kind": "stabilizedPercentage",
                "inputs": ["made", "attempted"],
                "priorAttempts": 150,
            },
            "attemptRate": {"kind": "ratio", "inputs": ["attempted", "minutes"]},
            "availability": {
                "kind": "scheduledRatio",
                "inputs": ["games", "season"],
                "schedule": {"2021": 72, "2022": 82},
            },
        },
        "cohorts": {"season": {"groupBy": ["season"]}},
        "eligibilityRules": {
            "standard": {
                "requiredMetrics": ["games", "minutes"],
                "minimumSamples": {"games": 20, "minutes": 500},
            }
        },
        "ratingScales": {
            "skill": {
                "minimum": 25,
                "maximum": 99,
                "anchors": [
                    {"percentile": 0, "rating": 25},
                    {"percentile": 0.5, "rating": 68},
                    {"percentile": 1, "rating": 99},
                ],
            },
            "overall": {
                "minimum": 25,
                "maximum": 99,
                "anchors": [
                    {"percentile": 0, "rating": 50},
                    {"percentile": 0.5, "rating": 67},
                    {"percentile": 1, "rating": 97},
                ],
            },
        },
        "attributes": [
            {
                "name": "insideScoring",
                "components": [
                    {
                        "metric": "adjustedPercentage",
                        "weight": 2,
                        "direction": "higher",
                    },
                    {"metric": "attemptRate", "weight": 1, "direction": "higher"},
                ],
                "eligibilityRule": "standard",
                "cohort": "season",
                "ratingScale": "skill",
                "rerankComposite": True,
            },
            {
                "name": "overall",
                "components": [
                    {"metric": "availability", "weight": 1, "direction": "higher"}
                ],
                "eligibilityRule": "standard",
                "cohort": "season",
                "ratingScale": "overall",
                "rerankComposite": True,
                "percentileOutput": "impactPercentile",
            },
        ],
        "talentTiers": [
            {"name": "fringe", "minimum": 25, "maximum": 67},
            {"name": "rotation", "minimum": 68, "maximum": 75},
            {"name": "starter", "minimum": 76, "maximum": 83},
            {"name": "all_star", "minimum": 84, "maximum": 89},
            {"name": "superstar", "minimum": 90, "maximum": 99},
        ],
    }


def test_parse_formula_document_returns_typed_normalized_contract() -> None:
    parsed = parse_formula_document(_document())

    assert isinstance(parsed, FormulaDocument)
    assert parsed.schema_version == 1
    assert parsed.formula_version == "1.0.0"
    assert parsed.rules["percentileMethod"] == "rankPct"
    assert parsed.metrics["availability"].dependencies == ("games", "season")
    assert parsed.metrics["availability"].schedule == {"2021": 72.0, "2022": 82.0}
    assert parsed.rating_scales["skill"].anchors[1].percentile == 0.5
    assert parsed.rating_scales["skill"].anchors[1].rating == 68
    assert [component.normalized_weight for component in parsed.attributes[0].components] == [
        pytest.approx(2 / 3),
        pytest.approx(1 / 3),
    ]


@pytest.mark.parametrize("version", [0, 2, -1])
def test_rejects_unsupported_schema_versions(version: int) -> None:
    document = _document()
    document["schemaVersion"] = version

    with pytest.raises(FormulaContractError, match="Unsupported formula schema version"):
        parse_formula_document(document)


@pytest.mark.parametrize("version", ["1", True, 1.0])
def test_rejects_non_integer_schema_versions(version: object) -> None:
    document = _document()
    document["schemaVersion"] = version

    with pytest.raises(FormulaContractError, match="schemaVersion must be an integer"):
        parse_formula_document(document)


@pytest.mark.parametrize(
    ("weight", "message"),
    [
        (-1, "nonnegative"),
        (float("nan"), "finite"),
        (float("inf"), "finite"),
        (True, "finite"),
    ],
)
def test_rejects_invalid_component_weights(weight: object, message: str) -> None:
    document = _document()
    document["attributes"][0]["components"][0]["weight"] = weight

    with pytest.raises(FormulaContractError, match=message):
        parse_formula_document(document)


def test_rejects_zero_sum_component_weights() -> None:
    document = _document()
    for component in document["attributes"][0]["components"]:
        component["weight"] = 0

    with pytest.raises(FormulaContractError, match="positive sum"):
        parse_formula_document(document)


def test_large_finite_component_weights_normalize_without_overflow() -> None:
    document = _document()
    for component in document["attributes"][0]["components"]:
        component["weight"] = 1e308

    parsed = parse_formula_document(document)

    assert [
        component.normalized_weight for component in parsed.attributes[0].components
    ] == [0.5, 0.5]


def test_rejects_duplicate_and_unknown_components() -> None:
    duplicate = _document()
    duplicate["attributes"][0]["components"][1]["metric"] = "adjustedPercentage"
    with pytest.raises(FormulaContractError, match="duplicate component"):
        parse_formula_document(duplicate)

    unknown = _document()
    unknown["attributes"][0]["components"][0]["metric"] = "pythonExpression"
    with pytest.raises(FormulaContractError, match="unknown metric"):
        parse_formula_document(unknown)


@pytest.mark.parametrize("direction", ["inverse", "ascending", 1, None])
def test_rejects_invalid_component_directions(direction: object) -> None:
    document = _document()
    document["attributes"][0]["components"][0]["direction"] = direction

    with pytest.raises(FormulaContractError, match="higher.*lower"):
        parse_formula_document(document)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (("minimum", 24), "25-99"),
        (("maximum", 100), "25-99"),
        (("firstPercentile", 0.1), "start at 0"),
        (("lastPercentile", 0.9), "end at 1"),
        (("middlePercentile", 0), "strictly increasing"),
        (("middleRating", 20), "within the 25-99"),
        (("lastRating", 60), "monotonic"),
    ],
)
def test_rejects_invalid_rating_scales(
    mutation: tuple[str, int | float], message: str
) -> None:
    document = _document()
    scale = document["ratingScales"]["skill"]
    field, value = mutation
    if field in {"minimum", "maximum"}:
        scale[field] = value
    elif field == "firstPercentile":
        scale["anchors"][0]["percentile"] = value
    elif field == "lastPercentile":
        scale["anchors"][-1]["percentile"] = value
    elif field == "middlePercentile":
        scale["anchors"][1]["percentile"] = value
    elif field == "middleRating":
        scale["anchors"][1]["rating"] = value
    else:
        scale["anchors"][-1]["rating"] = value

    with pytest.raises(FormulaContractError, match=message):
        parse_formula_document(document)


@pytest.mark.parametrize("kind", ["expression", "python", "sql", "custom"])
def test_rejects_unknown_derived_metric_kinds(kind: str) -> None:
    document = _document()
    document["metrics"]["attemptRate"]["kind"] = kind

    with pytest.raises(FormulaContractError, match="kind must be"):
        parse_formula_document(document)


def test_rejects_arbitrary_expression_fields() -> None:
    document = _document()
    document["metrics"]["attemptRate"]["expression"] = "__import__('os').system('x')"

    with pytest.raises(FormulaContractError, match="unknown keys: expression"):
        parse_formula_document(document)


def test_rejects_invalid_metric_dependencies() -> None:
    unknown = _document()
    unknown["metrics"]["attemptRate"]["inputs"][0] = "missingMetric"
    with pytest.raises(FormulaContractError, match="unknown metric"):
        parse_formula_document(unknown)

    cycle = _document()
    cycle["metrics"]["attemptRate"]["inputs"] = ["availability", "minutes"]
    cycle["metrics"]["availability"]["inputs"] = ["games", "attemptRate"]
    with pytest.raises(FormulaContractError, match="dependency cycle"):
        parse_formula_document(cycle)


def test_rejects_input_fields_outside_the_reference_contract() -> None:
    document = _document()
    document["metrics"]["made"]["field"] = "madeUpMetric"

    with pytest.raises(FormulaContractError, match="outside reference contract version 1"):
        parse_formula_document(document)


def test_stabilized_percentages_require_the_season_metric() -> None:
    document = _document()
    document["metrics"].pop("season")
    document["metrics"].pop("availability")
    document["cohorts"]["season"]["groupBy"] = ["games"]

    with pytest.raises(FormulaContractError, match="require.*season"):
        parse_formula_document(document)

    derived_season = _document()
    derived_season["metrics"]["season"] = {
        "kind": "ratio",
        "inputs": ["adjustedPercentage", "games"],
    }
    with pytest.raises(FormulaContractError, match="input mapped.*season"):
        parse_formula_document(derived_season)


@pytest.mark.parametrize(
    ("metric", "field", "value", "message"),
    [
        ("attemptRate", "inputs", ["attempted"], "exactly 2"),
        ("adjustedPercentage", "priorAttempts", 0, "positive"),
        ("availability", "schedule", {}, "must not be empty"),
        ("availability", "schedule", {"2021": 0}, "at least 1"),
        ("availability", "schedule", {"2021": 82.5}, "integer"),
        (
            "availability",
            "schedule",
            {"2021.0": 82},
            "canonical four-digit seasons",
        ),
        (
            "availability",
            "schedule",
            {"not-a-season": 82},
            "canonical four-digit seasons",
        ),
    ],
)
def test_rejects_invalid_derived_metric_parameters(
    metric: str, field: str, value: object, message: str
) -> None:
    document = _document()
    document["metrics"][metric][field] = value

    with pytest.raises(FormulaContractError, match=message):
        parse_formula_document(document)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("eligibilityRule", "missing", "unknown eligibility"),
        ("cohort", "missing", "unknown cohort"),
        ("ratingScale", "missing", "unknown rating scale"),
    ],
)
def test_rejects_unknown_named_attribute_references(
    field: str, value: str, message: str
) -> None:
    document = _document()
    document["attributes"][0][field] = value

    with pytest.raises(FormulaContractError, match=message):
        parse_formula_document(document)


def test_rejects_unknown_cohort_and_eligibility_metrics() -> None:
    cohort = _document()
    cohort["cohorts"]["season"]["groupBy"] = ["missing"]
    with pytest.raises(FormulaContractError, match="unknown metrics"):
        parse_formula_document(cohort)

    eligibility = _document()
    eligibility["eligibilityRules"]["standard"]["minimumSamples"] = {"missing": 20}
    with pytest.raises(FormulaContractError, match="unknown metrics"):
        parse_formula_document(eligibility)

    unrequired_threshold = _document()
    unrequired_threshold["eligibilityRules"]["standard"]["requiredMetrics"].remove("games")
    with pytest.raises(FormulaContractError, match="minimumSamples metrics must also be required"):
        parse_formula_document(unrequired_threshold)


@pytest.mark.parametrize(
    ("rule", "value"),
    [
        ("nullHandling", "medianFill"),
        ("percentileMethod", "quantile"),
        ("tieMethod", "first"),
        ("ratingRounding", "floor"),
    ],
)
def test_rejects_non_deterministic_or_unsupported_rules(rule: str, value: str) -> None:
    document = _document()
    document["rules"][rule] = value

    with pytest.raises(FormulaContractError, match=rule):
        parse_formula_document(document)


def test_rejects_invalid_versioned_tier_ranges() -> None:
    overlap = _document()
    overlap["talentTiers"][1]["minimum"] = 67
    with pytest.raises(FormulaContractError, match="must not overlap"):
        parse_formula_document(overlap)

    gap = _document()
    gap["talentTiers"][1]["minimum"] = 69
    with pytest.raises(FormulaContractError, match="cover every rating"):
        parse_formula_document(gap)

    outside = _document()
    outside["talentTiers"][0]["minimum"] = 24
    with pytest.raises(FormulaContractError, match="within 25-99"):
        parse_formula_document(outside)


def test_rejects_missing_formula_outputs_and_duplicate_output_fields() -> None:
    missing = _document()
    missing["outputFields"].remove("impactPercentile")
    with pytest.raises(FormulaContractError, match="exactly match the ordered formula outputs"):
        parse_formula_document(missing)

    duplicate = _document()
    duplicate["outputFields"].append("overall")
    with pytest.raises(FormulaContractError, match="duplicate names"):
        parse_formula_document(duplicate)

    missing_player_id = _document()
    missing_player_id["outputFields"].remove("playerId")
    with pytest.raises(FormulaContractError, match="exactly match.*playerId"):
        parse_formula_document(missing_player_id)


def test_rejects_reserved_colliding_and_orphan_outputs() -> None:
    reserved = _document()
    reserved["attributes"][0]["name"] = "playerId"
    with pytest.raises(FormulaContractError, match="reserved output field"):
        parse_formula_document(reserved)

    duplicate_percentile = _document()
    duplicate_percentile["attributes"][0]["percentileOutput"] = "impactPercentile"
    with pytest.raises(FormulaContractError, match="duplicate percentile outputs"):
        parse_formula_document(duplicate_percentile)

    orphan = _document()
    orphan["outputFields"].insert(-2, "unsupportedPlaceholder")
    with pytest.raises(FormulaContractError, match="exactly match the ordered formula outputs"):
        parse_formula_document(orphan)


def test_rejects_unsupported_reference_contract_version() -> None:
    document = _document()
    document["referenceContractVersion"] = 999

    with pytest.raises(FormulaContractError, match="Unsupported reference contract version 999"):
        parse_formula_document(document)


def test_rejects_unknown_top_level_fields() -> None:
    document = deepcopy(_document())
    document["executableCode"] = "lambda row: row"

    with pytest.raises(FormulaContractError, match="unknown keys: executableCode"):
        parse_formula_document(document)
