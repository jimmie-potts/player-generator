from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd
import pytest
from player_attribute_engine import (
    assign_talent_tier,
    evaluate_player_attributes,
    load_formula,
)

EXPECTED_OUTPUT_FIELDS = (
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

EXPECTED_COMPONENTS = {
    "insideScoring": (
        ("adjustedTwoPointPercentage", 0.50, "higher"),
        ("twoPointAttemptFrequency", 0.30, "higher"),
        ("freeThrowRate", 0.20, "higher"),
    ),
    "threePointShooting": (
        ("adjustedThreePointPercentage", 0.60, "higher"),
        ("threePointAttemptFrequency", 0.40, "higher"),
    ),
    "freeThrowShooting": (("adjustedFreeThrowPercentage", 1.00, "higher"),),
    "scoringVolume": (
        ("pointsPer100", 0.50, "higher"),
        ("usagePercentage", 0.30, "higher"),
        ("trueShootingPercentage", 0.20, "higher"),
    ),
    "playmaking": (
        ("assistPercentage", 0.30, "higher"),
        ("assistsPer36", 0.25, "higher"),
        ("assistRatio", 0.15, "higher"),
        ("assistTurnoverRatio", 0.15, "higher"),
        ("usagePercentage", 0.15, "higher"),
    ),
    "ballSecurity": (
        ("estimatedTurnoverPercentage", 0.40, "lower"),
        ("assistTurnoverRatio", 0.30, "higher"),
        ("turnoversPer100", 0.30, "lower"),
    ),
    "offensiveRebounding": (("offensiveReboundPercentage", 1.00, "higher"),),
    "defensiveRebounding": (("defensiveReboundPercentage", 1.00, "higher"),),
    "perimeterDefense": (
        ("stealsPer100", 0.45, "higher"),
        ("estimatedDefensiveRating", 0.20, "lower"),
        ("defensiveWinSharesPer36", 0.15, "higher"),
        ("defensiveReboundPercentage", 0.10, "higher"),
        ("playerImpactEstimate", 0.10, "higher"),
    ),
    "interiorDefense": (
        ("blocksPer100", 0.35, "higher"),
        ("defensiveReboundPercentage", 0.25, "higher"),
        ("estimatedDefensiveRating", 0.20, "lower"),
        ("defensiveWinSharesPer36", 0.10, "higher"),
        ("playerImpactEstimate", 0.10, "higher"),
    ),
    "stamina": (
        ("minutesPerGame", 0.80, "higher"),
        ("minutes", 0.20, "higher"),
    ),
    "durability": (("availability", 1.00, "higher"),),
    "overall": (
        ("playerImpactEstimate", 0.35, "higher"),
        ("estimatedNetRating", 0.20, "higher"),
        ("pointsPer100", 0.15, "higher"),
        ("minutesPerGame", 0.12, "higher"),
        ("trueShootingPercentage", 0.10, "higher"),
        ("availability", 0.08, "higher"),
    ),
}

EXPECTED_SKILL_ANCHORS = (
    (0.00, 25.0),
    (0.05, 38.0),
    (0.25, 54.0),
    (0.50, 68.0),
    (0.75, 80.0),
    (0.90, 90.0),
    (0.98, 97.0),
    (1.00, 99.0),
)

EXPECTED_OVERALL_ANCHORS = (
    (0.00, 50.0),
    (0.05, 53.0),
    (0.25, 60.0),
    (0.50, 67.0),
    (0.75, 74.0),
    (0.90, 82.0),
    (0.97, 89.0),
    (0.99, 94.0),
    (1.00, 97.0),
)

EXPECTED_TIERS = (
    ("fringe", 25, 67),
    ("rotation", 68, 75),
    ("starter", 76, 83),
    ("all_star", 84, 89),
    ("superstar", 90, 99),
)


def _synthetic_row(player_id: str, ordinal: int, **overrides: object) -> dict[str, object]:
    score = float(ordinal)
    row: dict[str, object] = {
        "playerId": player_id,
        "season": 2026,
        "games": 60,
        "minutes": 700.0 + score * 3.0,
        "minutesPerGame": 12.0 + score / 20.0,
        "fieldGoalsAttempted": 500.0,
        "twoPointersMade": 40.0 + score / 10.0,
        "twoPointersAttempted": 200.0,
        "threePointersMade": 20.0 + score / 20.0,
        "threePointersAttempted": 100.0,
        "freeThrowsMade": 30.0 + score / 20.0,
        "freeThrowsAttempted": 80.0,
        "twoPointAttemptFrequency": 0.30 + score / 2000.0,
        "threePointAttemptFrequency": 0.20 + score / 3000.0,
        "pointsPer100": 70.0 + score / 10.0,
        "usagePercentage": 10.0 + score / 20.0,
        "trueShootingPercentage": 0.40 + score / 2000.0,
        "assistPercentage": 5.0 + score / 20.0,
        "assistsPer36": 1.0 + score / 100.0,
        "assistRatio": 5.0 + score / 30.0,
        "assistTurnoverRatio": 0.50 + score / 200.0,
        "estimatedTurnoverPercentage": 20.0 - score / 100.0,
        "turnoversPer100": 6.0 - score / 1000.0,
        "offensiveReboundPercentage": 1.0 + score / 100.0,
        "defensiveReboundPercentage": 5.0 + score / 30.0,
        "stealsPer100": 0.20 + score / 500.0,
        "blocksPer100": 0.10 + score / 600.0,
        "estimatedDefensiveRating": 125.0 - score / 20.0,
        "defensiveWinSharesPer36": 0.01 + score / 10000.0,
        "playerImpactEstimate": 0.01 + score / 1000.0,
        "estimatedNetRating": -15.0 + score / 10.0,
    }
    row.update(overrides)
    return row


def _anchors(scale: object) -> tuple[tuple[float, float], ...]:
    return tuple((anchor.percentile, anchor.rating) for anchor in scale.anchors)


def _expected_rating(percentile: float, anchors: tuple[tuple[float, float], ...]) -> int:
    for (low_percentile, low_rating), (high_percentile, high_rating) in zip(
        anchors, anchors[1:], strict=True
    ):
        if percentile <= high_percentile:
            distance = (percentile - low_percentile) / (high_percentile - low_percentile)
            return round(low_rating + distance * (high_rating - low_rating))
    return round(anchors[-1][1])


def _reconstruct_metric(detail: Mapping[str, Any]) -> float | None:
    kind = detail["kind"]
    value = detail["value"]
    if kind == "input":
        return value

    inputs = {name: _reconstruct_metric(item) for name, item in detail["inputs"].items()}
    numerator, denominator = inputs.values()
    if numerator is None or denominator is None:
        return None
    if kind == "ratio":
        return detail["zeroDenominatorValue"] if denominator == 0 else numerator / denominator
    if kind == "stabilizedPercentage":
        prior_attempts = detail["priorAttempts"]
        return (numerator + detail["leagueAverage"] * prior_attempts) / (
            denominator + prior_attempts
        )
    if kind == "scheduledRatio":
        scheduled_games = detail["scheduledGames"]
        if scheduled_games is None or scheduled_games == 0:
            return None
        return max(detail["minimum"], min(detail["maximum"], numerator / scheduled_games))
    raise AssertionError(f"Unexpected metric kind: {kind}")


def test_active_formula_resource_is_the_approved_initial_model() -> None:
    formula = load_formula()

    assert formula.schema_version == 1
    assert formula.formula_version == "1.0.0"
    assert formula.reference_contract_version == 1
    assert formula.output_fields == EXPECTED_OUTPUT_FIELDS
    assert formula.rules == {
        "nullHandling": "exclude",
        "percentileMethod": "rankPct",
        "tieMethod": "average",
        "ratingRounding": "halfEven",
    }
    assert {
        attribute.name: tuple(
            (component.metric, component.weight, component.direction)
            for component in attribute.components
        )
        for attribute in formula.attributes
    } == EXPECTED_COMPONENTS
    assert all(attribute.eligibility_rule == "standardSeason" for attribute in formula.attributes)
    assert all(attribute.cohort == "season" for attribute in formula.attributes)
    assert all(attribute.rerank_composite for attribute in formula.attributes)
    assert {attribute.name: attribute.rating_scale for attribute in formula.attributes} == {
        **dict.fromkeys(EXPECTED_COMPONENTS, "skill"),
        "overall": "overall",
    }
    assert {
        attribute.name: attribute.percentile_output for attribute in formula.attributes
    } == {**dict.fromkeys(EXPECTED_COMPONENTS), "overall": "impactPercentile"}

    eligibility = formula.eligibility_rules["standardSeason"]
    assert eligibility.required_metrics == ("games", "minutes")
    assert eligibility.minimum_samples == {"games": 20.0, "minutes": 500.0}
    assert formula.cohorts["season"].group_by == ("season",)
    assert {
        name: formula.metrics[name].prior_attempts
        for name in (
            "adjustedTwoPointPercentage",
            "adjustedThreePointPercentage",
            "adjustedFreeThrowPercentage",
        )
    } == {
        "adjustedTwoPointPercentage": 150.0,
        "adjustedThreePointPercentage": 100.0,
        "adjustedFreeThrowPercentage": 75.0,
    }
    assert formula.metrics["availability"].schedule == {
        "2021": 72,
        "2022": 82,
        "2023": 82,
        "2024": 82,
        "2025": 82,
        "2026": 82,
    }
    assert (formula.rating_scales["skill"].minimum, formula.rating_scales["skill"].maximum) == (
        25,
        99,
    )
    assert (
        formula.rating_scales["overall"].minimum,
        formula.rating_scales["overall"].maximum,
    ) == (25, 99)
    assert _anchors(formula.rating_scales["skill"]) == EXPECTED_SKILL_ANCHORS
    assert _anchors(formula.rating_scales["overall"]) == EXPECTED_OVERALL_ANCHORS
    assert tuple(
        (tier.name, tier.minimum, tier.maximum) for tier in formula.talent_tiers
    ) == EXPECTED_TIERS


@pytest.mark.parametrize(
    ("rating", "expected_tier"),
    [
        (25, "fringe"),
        (67, "fringe"),
        (68, "rotation"),
        (75, "rotation"),
        (76, "starter"),
        (83, "starter"),
        (84, "all_star"),
        (89, "all_star"),
        (90, "superstar"),
        (99, "superstar"),
    ],
)
def test_every_talent_tier_boundary_is_inclusive(rating: int, expected_tier: str) -> None:
    assert assign_talent_tier(rating, load_formula()) == expected_tier


def test_approved_calibration_points_hold_in_a_fully_synthetic_376_player_cohort() -> None:
    frame = pd.DataFrame(
        [_synthetic_row(f"synthetic-rank-{ordinal:03d}", ordinal) for ordinal in range(1, 377)]
    )

    results = {
        row["playerId"]: row for row in evaluate_player_attributes(frame, load_formula()).rows
    }

    # The prior Jalen Duren outcome is a rank-based calibration point; no source row is copied.
    prior_duren_outcome = results["synthetic-rank-374"]
    assert prior_duren_outcome["impactPercentile"] == pytest.approx(374 / 376)
    assert prior_duren_outcome["impactPercentile"] == pytest.approx(0.9946808511)
    assert prior_duren_outcome["overall"] == 95
    assert prior_duren_outcome["talentTier"] == "superstar"

    # The prior Giannis Antetokounmpo outcome is isolated the same way.
    prior_giannis_outcome = results["synthetic-rank-358"]
    assert prior_giannis_outcome["impactPercentile"] == pytest.approx(358 / 376)
    assert prior_giannis_outcome["impactPercentile"] == pytest.approx(0.9521276596)
    assert prior_giannis_outcome["overall"] == 87
    assert prior_giannis_outcome["talentTier"] == "all_star"


def _representative_rows() -> list[dict[str, object]]:
    return [
        _synthetic_row("baseline-1", 1),
        _synthetic_row("baseline-2", 2),
        _synthetic_row("baseline-3", 3),
        _synthetic_row("baseline-4", 4),
        _synthetic_row("representative-starter", 7),
        _synthetic_row(
            "outside-specialist",
            3,
            threePointersMade=90.0,
            threePointAttemptFrequency=0.70,
        ),
        _synthetic_row("representative-star", 10),
        _synthetic_row("excluded-low-minute", 9, games=19, minutes=499),
        _synthetic_row("excluded-null-overall", 8, playerImpactEstimate=None),
    ]


def test_representative_player_snapshot() -> None:
    batch = evaluate_player_attributes(pd.DataFrame(_representative_rows()), load_formula())
    results = {row["playerId"]: row for row in batch.rows}
    explanations = {item["playerId"]: item for item in batch.explanations}

    snapshot_fields = (
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
    assert {
        player_id: {field: results[player_id][field] for field in snapshot_fields}
        for player_id in (
            "representative-star",
            "representative-starter",
            "outside-specialist",
        )
    } == {
        "representative-star": {
            "insideScoring": 99,
            "threePointShooting": 88,
            "freeThrowShooting": 99,
            "scoringVolume": 99,
            "playmaking": 99,
            "ballSecurity": 99,
            "offensiveRebounding": 99,
            "defensiveRebounding": 99,
            "perimeterDefense": 99,
            "interiorDefense": 99,
            "stamina": 99,
            "durability": 71,
            "overall": 97,
            "impactPercentile": 1.0,
            "talentTier": "superstar",
            "formulaVersion": "1.0.0",
        },
        "representative-starter": {
            "insideScoring": 80,
            "threePointShooting": 74,
            "freeThrowShooting": 80,
            "scoringVolume": 80,
            "playmaking": 80,
            "ballSecurity": 80,
            "offensiveRebounding": 80,
            "defensiveRebounding": 80,
            "perimeterDefense": 87,
            "interiorDefense": 87,
            "stamina": 80,
            "durability": 71,
            "overall": 80,
            "impactPercentile": 6 / 7,
            "talentTier": "starter",
            "formulaVersion": "1.0.0",
        },
        "outside-specialist": {
            "insideScoring": 64,
            "threePointShooting": 99,
            "freeThrowShooting": 64,
            "scoringVolume": 64,
            "playmaking": 64,
            "ballSecurity": 64,
            "offensiveRebounding": 64,
            "defensiveRebounding": 64,
            "perimeterDefense": 68,
            "interiorDefense": 68,
            "stamina": 64,
            "durability": 71,
            "overall": 67,
            "impactPercentile": 0.5,
            "talentTier": "fringe",
            "formulaVersion": "1.0.0",
        },
    }

    low_minute = results["excluded-low-minute"]
    assert all(low_minute[attribute] is None for attribute in EXPECTED_COMPONENTS)
    assert low_minute["impactPercentile"] is None
    assert low_minute["talentTier"] is None
    low_minute_reasons = explanations["excluded-low-minute"]["attributes"]["overall"][
        "ineligibilityReasons"
    ]
    assert low_minute_reasons == [
        {"kind": "minimumSample", "metric": "games", "minimum": 20.0, "actual": 19.0},
        {"kind": "minimumSample", "metric": "minutes", "minimum": 500.0, "actual": 499.0},
    ]

    null_overall = results["excluded-null-overall"]
    assert null_overall["overall"] is None
    assert null_overall["impactPercentile"] is None
    assert null_overall["talentTier"] is None
    assert explanations["excluded-null-overall"]["attributes"]["overall"][
        "ineligibilityReasons"
    ] == [{"kind": "missingMetric", "metric": "playerImpactEstimate"}]
    assert null_overall["threePointShooting"] is not None


def test_explanations_reconstruct_every_component_and_final_result() -> None:
    formula = load_formula()
    batch = evaluate_player_attributes(
        pd.DataFrame(
            [
                _synthetic_row(f"reconstruction-{ordinal}", ordinal)
                for ordinal in range(1, 13)
            ]
        ),
        formula,
    )
    result_by_player = {row["playerId"]: row for row in batch.rows}

    for attribute in formula.attributes:
        attribute_details = [
            explanation["attributes"][attribute.name] for explanation in batch.explanations
        ]
        expected_composite_percentiles = pd.Series(
            [detail["composite"] for detail in attribute_details]
        ).rank(method="average", pct=True)
        scale = formula.rating_scales[attribute.rating_scale]
        anchors = _anchors(scale)

        for index, (result, explanation, detail) in enumerate(
            zip(batch.rows, batch.explanations, attribute_details, strict=True)
        ):
            assert explanation["formulaVersion"] == formula.formula_version
            assert detail["eligible"] is True
            assert detail["ineligibilityReasons"] == []
            assert detail["cohort"] == {
                "name": "season",
                "values": {"season": 2026.0},
                "eligibleCount": 12,
            }

            reconstructed_contributions = {}
            for component in attribute.components:
                metric = component.metric
                reconstructed_metric = _reconstruct_metric(detail["metricDetails"][metric])
                assert detail["rawInputs"][metric] == pytest.approx(reconstructed_metric)
                assert detail["normalizedWeights"][metric] == pytest.approx(
                    component.normalized_weight
                )
                reconstructed_contributions[metric] = (
                    detail["componentPercentiles"][metric] * component.normalized_weight
                )
                assert detail["contributions"][metric] == pytest.approx(
                    reconstructed_contributions[metric]
                )

            reconstructed_composite = sum(reconstructed_contributions.values())
            reconstructed_percentile = float(expected_composite_percentiles.iloc[index])
            reconstructed_rating = _expected_rating(reconstructed_percentile, anchors)
            assert detail["composite"] == pytest.approx(reconstructed_composite)
            assert detail["compositePercentile"] == pytest.approx(reconstructed_percentile)
            assert detail["rating"] == reconstructed_rating
            assert result[attribute.name] == reconstructed_rating

            if attribute.percentile_output is not None:
                assert result[attribute.percentile_output] == pytest.approx(
                    reconstructed_percentile
                )
                assert result["talentTier"] == assign_talent_tier(
                    reconstructed_rating, formula
                )
            assert result_by_player[explanation["playerId"]] == result
