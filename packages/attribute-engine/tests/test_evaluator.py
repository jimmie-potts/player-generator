from __future__ import annotations

import json
from types import SimpleNamespace

import pandas as pd
import pytest
from player_attribute_engine.evaluator import EvaluationError, evaluate_player_attributes
from player_attribute_engine.formula import load_formula
from player_attribute_engine.metrics import prepare_formula_metrics


def _item(**values: object) -> SimpleNamespace:
    return SimpleNamespace(**values)


def _formula() -> SimpleNamespace:
    metrics = {
        name: _item(kind="input", field=name, inputs=(), prior_attempts=None, schedule=None)
        for name in (
            "season",
            "games",
            "minutes",
            "made",
            "attempted",
            "freeThrowsAttempted",
            "fieldGoalsAttempted",
            "turnovers",
            "impact",
        )
    }
    metrics.update(
        {
            "adjustedPercentage": _item(
                kind="stabilizedPercentage",
                field=None,
                inputs=("made", "attempted"),
                prior_attempts=10,
                schedule=None,
            ),
            "freeThrowRate": _item(
                kind="ratio",
                field=None,
                inputs=("freeThrowsAttempted", "fieldGoalsAttempted"),
                prior_attempts=None,
                schedule=None,
            ),
            "availability": _item(
                kind="scheduledRatio",
                field=None,
                inputs=("games", "season"),
                prior_attempts=None,
                schedule={"2025": 82, "2026": 82},
            ),
        }
    )
    skill_scale = _item(
        minimum=25,
        maximum=99,
        anchors=(
            _item(percentile=0.0, rating=26),
            _item(percentile=1.0, rating=99),
        ),
    )
    overall_scale = _item(
        minimum=25,
        maximum=99,
        anchors=(
            _item(percentile=0.0, rating=50),
            _item(percentile=1.0, rating=99),
        ),
    )
    standard = _item(
        required_metrics=("games", "minutes"),
        minimum_samples={"games": 20, "minutes": 500},
    )
    return _item(
        formula_version="test-v1",
        output_fields=(
            "playerId",
            "shooting",
            "security",
            "overall",
            "impactPercentile",
            "talentTier",
            "formulaVersion",
        ),
        metrics=metrics,
        cohorts={"season": _item(group_by=("season",))},
        eligibility_rules={"standard": standard},
        rating_scales={"skill": skill_scale, "overall": overall_scale},
        attributes=(
            _item(
                name="shooting",
                components=(
                    _item(metric="adjustedPercentage", weight=3.0, direction="higher"),
                    _item(metric="freeThrowRate", weight=1.0, direction="higher"),
                ),
                eligibility_rule="standard",
                cohort="season",
                rating_scale="skill",
                rerank_composite=True,
                percentile_output=None,
            ),
            _item(
                name="security",
                components=(
                    _item(metric="turnovers", weight=1.0, direction="lower"),
                ),
                eligibility_rule="standard",
                cohort="season",
                rating_scale="skill",
                rerank_composite=True,
                percentile_output=None,
            ),
            _item(
                name="overall",
                components=(
                    _item(metric="impact", weight=4.0, direction="higher"),
                    _item(metric="availability", weight=1.0, direction="higher"),
                ),
                eligibility_rule="standard",
                cohort="season",
                rating_scale="overall",
                rerank_composite=True,
                percentile_output="impactPercentile",
            ),
        ),
        talent_tiers=(
            _item(name="fringe", minimum=25, maximum=67),
            _item(name="rotation", minimum=68, maximum=75),
            _item(name="starter", minimum=76, maximum=83),
            _item(name="all_star", minimum=84, maximum=89),
            _item(name="superstar", minimum=90, maximum=99),
        ),
    )


def _row(player_id: str, **overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "playerId": player_id,
        "season": 2026,
        "games": 50,
        "minutes": 1000,
        "made": 5,
        "attempted": 10,
        "freeThrowsAttempted": 5,
        "fieldGoalsAttempted": 10,
        "turnovers": 2,
        "impact": 0.1,
    }
    row.update(overrides)
    return row


def test_missing_formula_input_fails_before_evaluation() -> None:
    frame = pd.DataFrame([_row("a")]).drop(columns="fieldGoalsAttempted")

    with pytest.raises(EvaluationError, match="fieldGoalsAttempted"):
        evaluate_player_attributes(frame, _formula())


def test_stabilization_uses_full_season_before_eligibility_and_derived_ratios_clip() -> None:
    frame = pd.DataFrame(
        [
            _row(
                "a",
                made=10,
                attempted=10,
                freeThrowsAttempted=5,
                fieldGoalsAttempted=0,
                games=100,
            ),
            _row("b", made=0, attempted=10),
            _row("low-sample", made=90, attempted=90, games=1, minutes=10),
        ]
    )

    batch = evaluate_player_attributes(frame, _formula())
    detail = batch.explanations[0]["attributes"]

    # The 2026 league prior is (10 + 0 + 90) / (10 + 10 + 90), including the
    # low-sample player.
    assert detail["shooting"]["rawInputs"]["adjustedPercentage"] == pytest.approx(
        (10 + (100 / 110) * 10) / 20
    )
    adjusted_detail = detail["shooting"]["metricDetails"]["adjustedPercentage"]
    assert adjusted_detail["priorAttempts"] == 10
    assert adjusted_detail["leagueAverage"] == pytest.approx(100 / 110)
    assert adjusted_detail["inputs"]["made"]["value"] == 10
    assert adjusted_detail["inputs"]["attempted"]["value"] == 10
    assert detail["shooting"]["rawInputs"]["freeThrowRate"] == 0.0
    assert detail["overall"]["rawInputs"]["availability"] == 1.0
    assert batch.rows[2]["shooting"] is None
    assert {reason["kind"] for reason in detail["shooting"]["ineligibilityReasons"]} == set()
    assert {
        reason["kind"]
        for reason in batch.explanations[2]["attributes"]["shooting"][
            "ineligibilityReasons"
        ]
    } == {"minimumSample"}


def test_average_ties_inverse_direction_and_season_cohorts_are_deterministic() -> None:
    batch = evaluate_player_attributes(
        pd.DataFrame(
            [
                _row("tie-a", turnovers=1),
                _row("tie-b", turnovers=1),
                _row("worse", turnovers=3),
            ]
        ),
        _formula(),
    )

    assert batch.rows[0]["security"] == batch.rows[1]["security"]
    assert batch.rows[0]["security"] > batch.rows[2]["security"]
    assert batch.explanations[0]["attributes"]["security"]["cohort"] == {
        "name": "season",
        "values": {"season": 2026.0},
        "eligibleCount": 3,
    }


def test_null_component_is_excluded_and_remaining_singleton_ranks_at_one() -> None:
    batch = evaluate_player_attributes(
        pd.DataFrame([_row("missing", impact=None), _row("eligible", impact=0.1)]),
        _formula(),
    )

    assert batch.rows[0]["overall"] is None
    assert batch.explanations[0]["attributes"]["overall"]["ineligibilityReasons"] == [
        {"kind": "missingMetric", "metric": "impact"}
    ]
    assert batch.rows[1]["impactPercentile"] == 1.0
    assert batch.rows[1]["overall"] == 99
    assert batch.rows[1]["talentTier"] == "superstar"
    assert batch.explanations[1]["attributes"]["overall"]["cohort"][
        "eligibleCount"
    ] == 1


def test_null_ratio_numerator_is_not_converted_to_zero() -> None:
    batch = evaluate_player_attributes(
        pd.DataFrame(
            [
                _row(
                    "missing",
                    freeThrowsAttempted=None,
                    fieldGoalsAttempted=0,
                ),
                _row("eligible"),
            ]
        ),
        _formula(),
    )

    shooting = batch.explanations[0]["attributes"]["shooting"]
    assert shooting["rawInputs"]["freeThrowRate"] is None
    assert {reason["metric"] for reason in shooting["ineligibilityReasons"]} == {
        "freeThrowRate"
    }


def test_half_even_rounding_and_scale_clamping() -> None:
    batch = evaluate_player_attributes(
        pd.DataFrame([_row("better", turnovers=1), _row("worse", turnovers=2)]),
        _formula(),
    )

    assert batch.rows[0]["security"] == 99
    # The lower row's rankPct is .5: interpolation is 62.5 and half-even rounds to 62.
    assert batch.rows[1]["security"] == 62


def test_explanations_reconstruct_composites_and_are_json_serializable() -> None:
    batch = evaluate_player_attributes(
        pd.DataFrame([_row("a", made=8), _row("b", made=2)]),
        _formula(),
    )
    shooting = batch.explanations[0]["attributes"]["shooting"]

    assert shooting["normalizedWeights"] == {
        "adjustedPercentage": 0.75,
        "freeThrowRate": 0.25,
    }
    assert sum(shooting["contributions"].values()) == pytest.approx(shooting["composite"])
    assert shooting["rating"] == batch.rows[0]["shooting"]
    assert shooting["metricDetails"]["freeThrowRate"]["inputs"] == {
        "freeThrowsAttempted": {
            "kind": "input",
            "value": 5.0,
            "field": "freeThrowsAttempted",
        },
        "fieldGoalsAttempted": {
            "kind": "input",
            "value": 10.0,
            "field": "fieldGoalsAttempted",
        },
    }
    assert list(batch.rows[0]) == list(_formula().output_fields)
    assert batch.rows[0]["formulaVersion"] == "test-v1"
    json.dumps(batch.rows)
    json.dumps(batch.explanations)


def test_large_finite_weights_normalize_stably_during_evaluation() -> None:
    formula = _formula()
    formula.attributes[0].components = (
        _item(metric="adjustedPercentage", weight=1e308, direction="higher"),
        _item(metric="freeThrowRate", weight=1e308, direction="higher"),
    )

    batch = evaluate_player_attributes(
        pd.DataFrame([_row("a", made=8), _row("b", made=2)]),
        formula,
    )

    assert batch.explanations[0]["attributes"]["shooting"]["normalizedWeights"] == {
        "adjustedPercentage": 0.5,
        "freeThrowRate": 0.5,
    }


def test_input_aliases_read_an_immutable_source_snapshot() -> None:
    definitions = [
        ("season", _item(kind="input", field="games")),
        ("games", _item(kind="input", field="season")),
    ]

    for ordered in (definitions, list(reversed(definitions))):
        prepared = prepare_formula_metrics(
            pd.DataFrame([{"season": 2026, "games": 50}]),
            dict(ordered),
        )
        assert prepared.loc[0, "season"] == 50
        assert prepared.loc[0, "games"] == 2026


@pytest.mark.parametrize("value", [None, "", "   ", 7])
def test_invalid_player_ids_fail_before_evaluation(value: object) -> None:
    with pytest.raises(EvaluationError, match="non-empty string playerId"):
        evaluate_player_attributes(pd.DataFrame([_row(value)]), _formula())


def test_duplicate_players_and_multiple_cohorts_fail_before_evaluation() -> None:
    with pytest.raises(EvaluationError, match="duplicate playerId"):
        evaluate_player_attributes(
            pd.DataFrame([_row("duplicate"), _row("duplicate")]),
            _formula(),
        )

    with pytest.raises(EvaluationError, match="one percentile cohort per call"):
        evaluate_player_attributes(
            pd.DataFrame([_row("a", season=2025), _row("b", season=2026)]),
            _formula(),
        )


@pytest.mark.parametrize(
    "value",
    [
        "not-a-number",
        "1.5",
        1 + 2j,
        pd.Timestamp("2026-01-01"),
        float("inf"),
        float("-inf"),
        True,
    ],
)
def test_invalid_numeric_inputs_fail_before_evaluation(value: object) -> None:
    with pytest.raises(EvaluationError, match="finite numeric values or null"):
        evaluate_player_attributes(
            pd.DataFrame([_row("invalid", impact=value)]),
            _formula(),
        )


def test_temporal_null_input_remains_null() -> None:
    frame = pd.DataFrame([_row("missing", impact=pd.NaT)])
    assert str(frame["impact"].dtype).startswith("datetime64")

    batch = evaluate_player_attributes(frame, _formula())

    assert batch.rows[0]["overall"] is None
    assert batch.explanations[0]["attributes"]["overall"]["ineligibilityReasons"] == [
        {"kind": "missingMetric", "metric": "impact"}
    ]


def test_active_formula_document_evaluates_every_declared_attribute() -> None:
    formula = load_formula()
    base = {
        metric.field: 1.0
        for metric in formula.metrics.values()
        if metric.kind == "input" and metric.field is not None
    }
    base.update(
        {
            "playerId": "player-a",
            "season": 2026,
            "games": 50,
            "minutes": 1000,
            "minutesPerGame": 20,
            "fieldGoalsAttempted": 100,
            "twoPointersMade": 40,
            "twoPointersAttempted": 70,
            "threePointersMade": 10,
            "threePointersAttempted": 30,
            "freeThrowsMade": 20,
            "freeThrowsAttempted": 25,
        }
    )
    other = {
        **base,
        "playerId": "player-b",
        "playerImpactEstimate": 2.0,
        "estimatedNetRating": 2.0,
        "pointsPer100": 2.0,
    }

    batch = evaluate_player_attributes(pd.DataFrame([base, other]), formula)

    assert tuple(batch.rows[0]) == formula.output_fields
    assert batch.rows[0]["formulaVersion"] == formula.formula_version
    assert set(batch.explanations[0]["attributes"]) == {
        attribute.name for attribute in formula.attributes
    }
