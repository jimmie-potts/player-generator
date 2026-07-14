from __future__ import annotations

import copy
import hashlib
from importlib.resources import files
from typing import Any

import httpx2
import pytest

from conftest import SyntheticPackage, file_hashes

pytestmark = pytest.mark.anyio


def _assert_error_without_results(
    response: Any,
    *,
    status: int,
    code: str,
    field_codes: set[str] | None = None,
) -> dict[str, object]:
    assert response.status_code == status
    payload = response.json()
    assert set(payload) == {"error"}
    assert payload["error"]["code"] == code
    assert isinstance(payload["error"]["message"], str)
    assert "players" not in payload
    assert "results" not in payload
    fields_payload = payload["error"]["fields"]
    assert all(set(field) == {"path", "code", "message"} for field in fields_payload)
    if field_codes is not None:
        assert {field["code"] for field in fields_payload} == field_codes
    return payload


async def test_missing_player_errors_are_structured_and_return_no_results(
    client: httpx2.AsyncClient,
    request_payload: Any,
) -> None:
    detail = await client.get("/api/v1/players/not-a-player")
    detail_payload = _assert_error_without_results(
        detail,
        status=404,
        code="player_not_found",
        field_codes={"missing_player"},
    )
    assert detail_payload["error"]["fields"][0]["path"] == "playerId"

    preview = await client.post(
        "/api/v1/previews",
        json=request_payload(["player-star", "not-a-player"], {}),
    )
    preview_payload = _assert_error_without_results(
        preview,
        status=422,
        code="invalid_request",
        field_codes={"missing_player"},
    )
    assert preview_payload["error"]["fields"][0]["path"] == "selectedPlayerIds"

    baseline = await client.get(
        "/api/v1/players",
        params={"pinnedPlayerId": "not-a-player"},
    )
    _assert_error_without_results(
        baseline,
        status=422,
        code="invalid_request",
        field_codes={"missing_player"},
    )


async def test_stale_preview_context_reports_every_mismatched_identity(
    client: httpx2.AsyncClient,
    request_payload: Any,
) -> None:
    request = request_payload(["player-star"], {})
    request.update(
        {
            "referencePackageHash": "1" * 64,
            "formulaVersion": "stale-version",
            "formulaDocumentHash": "2" * 64,
        }
    )

    response = await client.post("/api/v1/previews", json=request)

    payload = _assert_error_without_results(
        response,
        status=409,
        code="stale_context",
        field_codes={"stale_reference_package", "stale_formula"},
    )
    assert {field["path"] for field in payload["error"]["fields"]} == {
        "referencePackageHash",
        "formulaVersion",
        "formulaDocumentHash",
    }


async def test_stale_season_is_an_atomic_context_conflict(
    client: httpx2.AsyncClient,
    request_payload: Any,
) -> None:
    request = request_payload(["player-star"], {})
    request["season"] = 2025

    response = await client.post("/api/v1/previews", json=request)

    payload = _assert_error_without_results(
        response,
        status=409,
        code="stale_context",
        field_codes={"stale_season"},
    )
    assert payload["error"]["fields"] == [
        {
            "path": "season",
            "code": "stale_season",
            "message": "Season does not match the loaded preview cohort.",
        }
    ]


@pytest.mark.parametrize(
    ("adjustments", "error_code", "field_code", "path"),
    [
        (
            {
                "components": [
                    {
                        "attribute": "unknownAttribute",
                        "metric": "pointsPer100",
                        "weight": 1.0,
                    }
                ]
            },
            "invalid_request",
            "unknown_attribute",
            "adjustments.components.0.attribute",
        ),
        (
            {
                "components": [
                    {
                        "attribute": "overall",
                        "metric": "notAComponent",
                        "weight": 1.0,
                    }
                ]
            },
            "invalid_request",
            "unknown_component",
            "adjustments.components.0.metric",
        ),
        (
            {
                "ratingScales": [
                    {
                        "scale": "unknownScale",
                        "anchors": [
                            {"percentile": 0.0, "rating": 25.0},
                            {"percentile": 1.0, "rating": 99.0},
                        ],
                    }
                ]
            },
            "invalid_request",
            "unknown_rating_scale",
            "adjustments.ratingScales.0.scale",
        ),
        (
            {
                "ratingScales": [
                    {
                        "scale": "overall",
                        "anchors": [
                            {"percentile": 0.0, "rating": 25.0},
                            {"percentile": 0.75, "rating": 80.0},
                            {"percentile": 0.5, "rating": 90.0},
                            {"percentile": 1.0, "rating": 99.0},
                        ],
                    }
                ]
            },
            "invalid_formula",
            "invalid_formula",
            "adjustments",
        ),
    ],
    ids=["attribute", "component", "scale", "anchor-order"],
)
async def test_invalid_adjustments_have_field_errors_and_no_partial_results(
    client: httpx2.AsyncClient,
    request_payload: Any,
    adjustments: dict[str, object],
    error_code: str,
    field_code: str,
    path: str,
) -> None:
    response = await client.post(
        "/api/v1/previews",
        json=request_payload(["player-star"], adjustments),
    )

    payload = _assert_error_without_results(
        response,
        status=422,
        code=error_code,
        field_codes={field_code},
    )
    assert payload["error"]["fields"][0]["path"] == path


async def test_zero_weight_formula_and_schema_validation_errors_are_structured(
    client: httpx2.AsyncClient,
    request_payload: Any,
) -> None:
    zero_weights = {
        "components": [
            {"attribute": "insideScoring", "metric": metric, "weight": 0.0}
            for metric in (
                "adjustedTwoPointPercentage",
                "twoPointAttemptFrequency",
                "freeThrowRate",
            )
        ]
    }
    formula_response = await client.post(
        "/api/v1/previews",
        json=request_payload(["player-star"], zero_weights),
    )
    _assert_error_without_results(
        formula_response,
        status=422,
        code="invalid_formula",
        field_codes={"invalid_formula"},
    )

    invalid_schema = request_payload(["player-star"], {})
    invalid_schema["adjustments"] = {
        "components": [
            {
                "attribute": "overall",
                "metric": "pointsPer100",
                "weight": -1,
            }
        ]
    }
    schema_response = await client.post("/api/v1/previews", json=invalid_schema)
    schema_payload = _assert_error_without_results(
        schema_response,
        status=422,
        code="invalid_request",
    )
    assert schema_payload["error"]["fields"][0]["path"] == (
        "adjustments.components.0.weight"
    )


async def test_duplicate_and_excessive_player_selections_fail_atomically(
    client: httpx2.AsyncClient,
    request_payload: Any,
) -> None:
    duplicate = await client.post(
        "/api/v1/previews",
        json=request_payload(["player-star", "player-star"], {}),
    )
    _assert_error_without_results(
        duplicate,
        status=422,
        code="invalid_request",
        field_codes={"duplicate"},
    )

    too_many = await client.post(
        "/api/v1/previews",
        json=request_payload(
            [
                "player-star",
                "player-starter",
                "player-impact",
                "player-volume",
                "player-shooter",
                "player-security",
            ],
            {},
        ),
    )
    _assert_error_without_results(
        too_many,
        status=422,
        code="invalid_request",
        field_codes={"too_many"},
    )


async def test_request_model_rejects_missing_context_and_unknown_fields(
    client: httpx2.AsyncClient,
    request_payload: Any,
) -> None:
    missing = request_payload(["player-star"], {})
    missing.pop("apiVersion")
    missing["unexpected"] = True

    response = await client.post("/api/v1/previews", json=missing)

    payload = _assert_error_without_results(
        response,
        status=422,
        code="invalid_request",
    )
    assert {field["path"] for field in payload["error"]["fields"]} == {
        "apiVersion",
        "unexpected",
    }


@pytest.mark.parametrize(
    ("field", "value", "path"),
    [
        ("weight", "0.5", "adjustments.components.0.weight"),
        ("inverseDirection", "true", "adjustments.components.0.inverseDirection"),
    ],
    ids=["string-weight", "string-boolean"],
)
async def test_preview_adjustments_reject_string_coercion(
    client: httpx2.AsyncClient,
    request_payload: Any,
    field: str,
    value: str,
    path: str,
) -> None:
    adjustment: dict[str, object] = {
        "attribute": "overall",
        "metric": "pointsPer100",
        field: value,
    }
    response = await client.post(
        "/api/v1/previews",
        json=request_payload(
            ["player-star"],
            {"components": [adjustment]},
        ),
    )

    payload = _assert_error_without_results(
        response,
        status=422,
        code="invalid_request",
    )
    assert [item["path"] for item in payload["error"]["fields"]] == [path]


@pytest.mark.parametrize(
    ("snake_name", "camel_name", "value", "expected_paths"),
    [
        (
            "api_version",
            "apiVersion",
            "1",
            {"apiVersion", "api_version"},
        ),
        (
            "selected_player_ids",
            "selectedPlayerIds",
            ["player-star"],
            {"selectedPlayerIds", "selected_player_ids"},
        ),
    ],
    ids=["api-version", "selected-players"],
)
async def test_preview_request_rejects_snake_case_wire_names(
    client: httpx2.AsyncClient,
    request_payload: Any,
    snake_name: str,
    camel_name: str,
    value: object,
    expected_paths: set[str],
) -> None:
    request = request_payload(["player-star"], {})
    request.pop(camel_name)
    request[snake_name] = value

    response = await client.post("/api/v1/previews", json=request)

    payload = _assert_error_without_results(
        response,
        status=422,
        code="invalid_request",
    )
    assert {item["path"] for item in payload["error"]["fields"]} == expected_paths


async def test_nested_preview_adjustments_reject_snake_case_wire_names(
    client: httpx2.AsyncClient,
    request_payload: Any,
) -> None:
    request = request_payload(
        ["player-star"],
        {
            "components": [
                {
                    "attribute": "overall",
                    "metric": "pointsPer100",
                    "weight": 0.5,
                    "inverse_direction": True,
                }
            ]
        },
    )

    response = await client.post("/api/v1/previews", json=request)

    payload = _assert_error_without_results(
        response,
        status=422,
        code="invalid_request",
    )
    assert [item["path"] for item in payload["error"]["fields"]] == [
        "adjustments.components.0.inverse_direction"
    ]


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
async def test_formula_endpoint_prevents_write_methods(
    client: httpx2.AsyncClient,
    method: str,
) -> None:
    response = await client.request(method.upper(), "/api/v1/formula", json={})

    _assert_error_without_results(
        response,
        status=405,
        code="method_not_allowed",
    )


async def test_valid_invalid_and_write_attempts_do_not_modify_formula_or_package_files(
    client: httpx2.AsyncClient,
    synthetic_package: SyntheticPackage,
    request_payload: Any,
) -> None:
    formula_resource = files("player_attribute_engine").joinpath(
        "formulas/player-attributes-v1.json"
    )
    formula_before = hashlib.sha256(formula_resource.read_bytes()).hexdigest()
    package_before = file_hashes(synthetic_package.path)

    valid = await client.post(
        "/api/v1/previews",
        json=request_payload(
            ["player-star"],
            {
                "components": [
                    {
                        "attribute": "overall",
                        "metric": "pointsPer100",
                        "weight": 0.9,
                    }
                ]
            },
        ),
    )
    assert valid.status_code == 200

    invalid_request = copy.deepcopy(request_payload(["player-star"], {}))
    invalid_request["referencePackageHash"] = "f" * 64
    invalid = await client.post("/api/v1/previews", json=invalid_request)
    assert invalid.status_code == 409

    rejected_write = await client.patch(
        "/api/v1/formula", json={"formulaVersion": "changed"}
    )
    assert rejected_write.status_code == 405

    assert hashlib.sha256(formula_resource.read_bytes()).hexdigest() == formula_before
    assert file_hashes(synthetic_package.path) == package_before
