from __future__ import annotations

import asyncio
import threading
from typing import Any

import httpx2
import pandas as pd
import pytest
from formula_preview_api import PreviewService, PreviewSettings, create_app

from conftest import SyntheticPackage, preview_request

pytestmark = pytest.mark.anyio


async def test_blocked_preview_calculation_does_not_block_read_endpoint(
    settings: PreviewSettings,
    service: PreviewService,
    synthetic_package: SyntheticPackage,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import formula_preview_api.service as service_module

    entered = threading.Event()
    release = threading.Event()
    evaluate = service_module.evaluate_player_attributes

    def blocked_evaluation(frame: pd.DataFrame, formula: Any):
        entered.set()
        release.wait(timeout=5)
        return evaluate(frame, formula)

    monkeypatch.setattr(service_module, "evaluate_player_attributes", blocked_evaluation)
    app = create_app(settings, service=service)
    preview_transport = httpx2.ASGITransport(app=app)
    read_transport = httpx2.ASGITransport(app=app)
    request = preview_request(
        synthetic_package,
        ["player-star"],
        adjustments={
            "components": [
                {
                    "attribute": "overall",
                    "metric": "pointsPer100",
                    "weight": 1.0,
                }
            ]
        },
    )

    async with (
        httpx2.AsyncClient(
            transport=preview_transport,
            base_url="http://test",
        ) as preview_client,
        httpx2.AsyncClient(
            transport=read_transport,
            base_url="http://test",
        ) as read_client,
    ):
        preview_task = asyncio.create_task(
            preview_client.post("/api/v1/previews", json=request)
        )
        try:
            loop = asyncio.get_running_loop()
            deadline = loop.time() + 2.0
            while not entered.is_set() and loop.time() < deadline:
                await asyncio.sleep(0.01)
            assert entered.is_set()
            assert not preview_task.done()

            read_response = await asyncio.wait_for(
                read_client.get("/api/v1/formula"),
                timeout=1.0,
            )
            assert read_response.status_code == 200
            assert read_response.json()["context"]["cohortSize"] == len(
                synthetic_package.cohort
            )
            assert not preview_task.done()
        finally:
            release.set()
        preview_response = await asyncio.wait_for(preview_task, timeout=5.0)

    assert preview_response.status_code == 200
    assert [player["playerId"] for player in preview_response.json()["players"]] == [
        "player-star"
    ]
