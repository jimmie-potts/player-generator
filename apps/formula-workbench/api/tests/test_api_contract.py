from __future__ import annotations

import copy
import json
from collections.abc import Collection, Mapping, Sequence
from typing import Any

import httpx2
import pandas as pd
import pytest
from formula_preview_api.service import PreviewService
from player_attribute_engine import evaluate_player_attributes, parse_formula_document

from conftest import SyntheticPackage

pytestmark = pytest.mark.anyio


def _assert_nested(actual: object, expected: object) -> None:
    if isinstance(expected, Mapping):
        assert isinstance(actual, Mapping)
        assert set(actual) == set(expected)
        for key, value in expected.items():
            _assert_nested(actual[key], value)
        return
    if isinstance(expected, list):
        assert isinstance(actual, list)
        assert len(actual) == len(expected)
        for actual_item, expected_item in zip(actual, expected, strict=True):
            _assert_nested(actual_item, expected_item)
        return
    if isinstance(expected, float):
        assert actual == pytest.approx(expected)
        return
    assert actual == expected


def _context(response: Mapping[str, Any]) -> Mapping[str, Any]:
    return response["context"]


async def test_formula_endpoint_returns_the_exact_active_document_and_identity(
    client: httpx2.AsyncClient,
    synthetic_package: SyntheticPackage,
) -> None:
    response = await client.get("/api/v1/formula")

    assert response.status_code == 200
    payload = response.json()
    assert payload["document"] == synthetic_package.formula_payload
    context = _context(payload)
    assert context == {
        "apiVersion": "1",
        "referencePackage": {
            "packageVersion": 2,
            "contentHash": synthetic_package.content_hash,
            "publishedFormulaVersion": synthetic_package.formula.formula_version,
            "publishedFormulaDocumentHash": synthetic_package.formula_hash,
        },
        "formula": {
            "schemaVersion": synthetic_package.formula.schema_version,
            "formulaVersion": synthetic_package.formula.formula_version,
            "documentHash": synthetic_package.formula_hash,
        },
        "season": 2026,
        "cohortSize": len(synthetic_package.cohort),
    }


async def test_metrics_endpoint_covers_every_formula_metric_and_component_usage(
    client: httpx2.AsyncClient,
    synthetic_package: SyntheticPackage,
) -> None:
    response = await client.get("/api/v1/metrics")

    assert response.status_code == 200
    metrics = response.json()["metrics"]
    assert [metric["name"] for metric in metrics] == list(
        synthetic_package.formula_payload["metrics"]
    )
    by_name = {metric["name"]: metric for metric in metrics}
    assert all(metric["label"] and metric["description"] for metric in metrics)
    for attribute in synthetic_package.formula_payload["attributes"]:
        for component in attribute["components"]:
            assert {
                "attribute": attribute["name"],
                "weight": component["weight"],
                "direction": component["direction"],
            } in by_name[component["metric"]]["usedBy"]
    assert by_name["adjustedThreePointPercentage"] == {
        "name": "adjustedThreePointPercentage",
        "label": "Adjusted Three Point Percentage",
        "description": (
            "Season-stabilized Three Pointers Made divided by Three Pointers Attempted "
            "using 100 prior attempts."
        ),
        "kind": "stabilizedPercentage",
        "field": None,
        "inputs": ["threePointersMade", "threePointersAttempted"],
        "priorAttempts": 100.0,
        "schedule": {},
        "usedBy": [
            {
                "attribute": "threePointShooting",
                "weight": 0.6,
                "direction": "higher",
            }
        ],
    }


async def test_baseline_is_bounded_ranked_and_augmented_by_pins(
    client: httpx2.AsyncClient,
    synthetic_package: SyntheticPackage,
) -> None:
    response = await client.get(
        "/api/v1/players",
        params=[("limit", "2"), ("pinnedPlayerId", "player-pinned")],
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["defaultSampleSize"] == 3
    assert len(payload["players"]) == 3
    default_players = payload["players"][:2]
    assert [player["baseline"]["overall"] for player in default_players] == sorted(
        [player["baseline"]["overall"] for player in default_players],
        reverse=True,
    )
    assert [player["baselineRank"] for player in default_players] == sorted(
        player["baselineRank"] for player in default_players
    )
    pinned = payload["players"][-1]
    assert pinned["playerId"] == "player-pinned"
    assert pinned["pinned"] is True
    assert sum(player["playerId"] == "player-pinned" for player in payload["players"]) == 1
    for player in payload["players"]:
        _assert_nested(
            player["baseline"],
            synthetic_package.rows_by_player[player["playerId"]],
        )

    already_default = default_players[0]["playerId"]
    duplicate_response = await client.get(
        "/api/v1/players",
        params=[("limit", "2"), ("pinnedPlayerId", already_default)],
    )
    assert duplicate_response.status_code == 200
    duplicate_players = duplicate_response.json()["players"]
    assert len(duplicate_players) == 2
    assert sum(player["playerId"] == already_default for player in duplicate_players) == 1
    assert next(player for player in duplicate_players if player["playerId"] == already_default)[
        "pinned"
    ] is True


@pytest.mark.parametrize(
    ("query", "expected_player"),
    [
        ("  JOSE\u0301---EXA  ", "player-shooter"),
        ("PLAYER SHOOT", "player-shooter"),
        ("volume", "player-volume"),
    ],
)
async def test_search_normalizes_unicode_punctuation_case_names_and_stable_ids(
    client: httpx2.AsyncClient,
    query: str,
    expected_player: str,
) -> None:
    response = await client.get("/api/v1/players/search", params={"q": query})

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == query
    assert payload["players"][0]["playerId"] == expected_player
    serialized = json.dumps(payload)
    assert "sourcePlayerId" not in serialized
    assert "upstream-player" not in serialized


async def test_player_detail_exposes_the_shared_engine_explanation(
    client: httpx2.AsyncClient,
    synthetic_package: SyntheticPackage,
) -> None:
    response = await client.get("/api/v1/players/player-shooter")

    assert response.status_code == 200
    payload = response.json()
    _assert_nested(payload["baseline"], synthetic_package.rows_by_player["player-shooter"])
    _assert_nested(
        payload["calculation"],
        synthetic_package.explanations_by_player["player-shooter"],
    )
    shooting = payload["calculation"]["attributes"]["threePointShooting"]
    assert shooting["eligible"] is True
    assert set(shooting) >= {
        "rawInputs",
        "componentPercentiles",
        "normalizedWeights",
        "contributions",
        "compositePercentile",
        "rating",
    }
    assert sum(shooting["normalizedWeights"].values()) == pytest.approx(1.0)
    assert sum(shooting["contributions"].values()) == pytest.approx(
        shooting["composite"]
    )


async def test_ineligible_player_detail_keeps_null_results_and_reasons(
    client: httpx2.AsyncClient,
) -> None:
    response = await client.get("/api/v1/players/player-low-minute")

    assert response.status_code == 200
    payload = response.json()
    assert payload["baseline"]["overall"] is None
    assert payload["player"]["baselineRank"] is None
    reasons = payload["calculation"]["attributes"]["overall"]["ineligibilityReasons"]
    assert reasons == [
        {"kind": "minimumSample", "metric": "games", "minimum": 20.0, "actual": 19.0},
        {
            "kind": "minimumSample",
            "metric": "minutes",
            "minimum": 500.0,
            "actual": 499.0,
        },
    ]


def _apply_adjustments(
    payload: dict[str, Any],
    adjustments: Mapping[str, object],
) -> dict[str, Any]:
    edited = copy.deepcopy(payload)
    attributes = {attribute["name"]: attribute for attribute in edited["attributes"]}
    for adjustment in adjustments.get("components", []):
        attribute = attributes[adjustment["attribute"]]
        component = next(
            component
            for component in attribute["components"]
            if component["metric"] == adjustment["metric"]
        )
        if "weight" in adjustment:
            component["weight"] = adjustment["weight"]
        if adjustment.get("inverseDirection"):
            component["direction"] = (
                "lower" if component["direction"] == "higher" else "higher"
            )
    for adjustment in adjustments.get("ratingScales", []):
        edited["ratingScales"][adjustment["scale"]]["anchors"] = adjustment["anchors"]
    return edited


def _ranks(rows: Sequence[Mapping[str, Any]]) -> dict[str, int | None]:
    values = pd.Series(
        {str(row["playerId"]): row.get("overall") for row in rows},
        dtype="Float64",
    )
    ranked = values.rank(method="min", ascending=False, na_option="keep")
    return {
        player_id: None if pd.isna(rank) else int(rank)
        for player_id, rank in ranked.items()
    }


@pytest.mark.parametrize(
    "adjustments",
    [
        {
            "components": [
                {
                    "attribute": "overall",
                    "metric": "playerImpactEstimate",
                    "weight": 0.0,
                }
            ]
        },
        {
            "components": [
                {
                    "attribute": "overall",
                    "metric": "playerImpactEstimate",
                    "inverseDirection": True,
                }
            ]
        },
        {
            "ratingScales": [
                {
                    "scale": "overall",
                    "anchors": [
                        {"percentile": 0.0, "rating": 25.0},
                        {"percentile": 0.5, "rating": 55.0},
                        {"percentile": 1.0, "rating": 99.0},
                    ],
                }
            ]
        },
    ],
    ids=["weight", "inverse-direction", "anchors"],
)
async def test_preview_edits_match_direct_shared_engine_evaluation(
    client: httpx2.AsyncClient,
    synthetic_package: SyntheticPackage,
    request_payload: Any,
    adjustments: dict[str, object],
) -> None:
    selected = [
        "player-star",
        "player-impact",
        "player-volume",
        "player-shooter",
        "player-pinned",
    ]
    expected_payload = _apply_adjustments(
        synthetic_package.formula_payload,
        adjustments,
    )
    expected_formula = parse_formula_document(expected_payload)
    expected_batch = evaluate_player_attributes(synthetic_package.cohort, expected_formula)
    expected_rows = {str(row["playerId"]): row for row in expected_batch.rows}
    expected_explanations = {
        str(row["playerId"]): row for row in expected_batch.explanations
    }
    expected_ranks = _ranks(expected_batch.rows)

    response = await client.post(
        "/api/v1/previews",
        json=request_payload(selected, adjustments),
    )

    assert response.status_code == 200
    result = response.json()
    assert result["previewFormulaHash"] != synthetic_package.formula_hash
    assert [player["playerId"] for player in result["players"]] == selected
    for player in result["players"]:
        player_id = player["playerId"]
        _assert_nested(player["preview"], expected_rows[player_id])
        _assert_nested(
            player["previewCalculation"],
            expected_explanations[player_id],
        )
        assert player["previewRank"] == expected_ranks[player_id]
        baseline_rank = player["baselineRank"]
        assert player["rankMovement"] == (
            None
            if baseline_rank is None or expected_ranks[player_id] is None
            else baseline_rank - expected_ranks[player_id]
        )
        for field, change in player["changes"].items():
            assert change["baselineValue"] == player["baseline"].get(field)
            assert change["previewValue"] == player["preview"].get(field)
            if isinstance(change["baselineValue"], (int, float)) and isinstance(
                change["previewValue"], (int, float)
            ):
                assert change["delta"] == pytest.approx(
                    change["previewValue"] - change["baselineValue"]
                )
            else:
                assert change["delta"] is None


async def test_preview_recalculates_the_full_cohort_for_one_selected_player(
    client: httpx2.AsyncClient,
    synthetic_package: SyntheticPackage,
    request_payload: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import formula_preview_api.service as service_module

    calls: list[tuple[int, str, frozenset[str] | None]] = []
    evaluate = service_module.evaluate_player_attributes

    def record(
        frame: pd.DataFrame,
        formula: Any,
        *,
        explanation_player_ids: Collection[str] | None = None,
    ):
        calls.append(
            (
                len(frame),
                str(formula.formula_version),
                None
                if explanation_player_ids is None
                else frozenset(explanation_player_ids),
            )
        )
        return evaluate(
            frame,
            formula,
            explanation_player_ids=explanation_player_ids,
        )

    monkeypatch.setattr(service_module, "evaluate_player_attributes", record)
    response = await client.post(
        "/api/v1/previews",
        json=request_payload(
            ["player-pinned"],
            {
                "components": [
                    {
                        "attribute": "overall",
                        "metric": "pointsPer100",
                        "weight": 1.0,
                    }
                ]
            },
        ),
    )

    assert response.status_code == 200
    assert calls == [
        (
            len(synthetic_package.cohort),
            synthetic_package.formula.formula_version,
            frozenset({"player-pinned"}),
        )
    ]
    assert [player["playerId"] for player in response.json()["players"]] == [
        "player-pinned"
    ]


async def test_identical_preview_requests_are_deterministic_except_for_timing(
    client: httpx2.AsyncClient,
    request_payload: Any,
) -> None:
    request = request_payload(["player-star", "player-volume"], {})

    first = await client.post("/api/v1/previews", json=request)
    second = await client.post("/api/v1/previews", json=request)

    assert first.status_code == second.status_code == 200
    first_payload = first.json()
    second_payload = second.json()
    assert first_payload.pop("elapsedMs") >= 0
    assert second_payload.pop("elapsedMs") >= 0
    assert first_payload == second_payload
    assert all(player["baseline"] == player["preview"] for player in first_payload["players"])
    assert all(player["rankMovement"] == 0 for player in first_payload["players"])


async def test_service_baseline_matches_the_fixture_shared_engine_output(
    service: PreviewService,
    synthetic_package: SyntheticPackage,
) -> None:
    baseline = service.baseline(
        limit=3,
        pinned_player_ids=tuple(
            player_id
            for player_id in synthetic_package.rows_by_player
            if player_id not in {
                item.player_id for item in service.baseline(limit=3).players
            }
        )[:1],
    )

    for player in baseline.players:
        _assert_nested(
            player.baseline,
            synthetic_package.rows_by_player[player.player_id],
        )
