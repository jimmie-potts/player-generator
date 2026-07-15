from __future__ import annotations

import csv
import json
import shutil
from dataclasses import replace
from pathlib import Path
from time import perf_counter

import formula_preview_api.service as service_module
import httpx2
import pytest
from formula_preview_api import PreviewService, PreviewSettings, create_app

from conftest import (
    SyntheticPackage,
    preview_request,
    refresh_manifest,
)

pytestmark = pytest.mark.anyio


def _copy_package(source: Path, destination: Path) -> Path:
    return Path(shutil.copytree(source, destination))


async def test_startup_rejects_missing_and_hash_mismatched_package_files(
    synthetic_package: SyntheticPackage,
    settings: PreviewSettings,
    tmp_path: Path,
) -> None:
    missing = _copy_package(synthetic_package.path, tmp_path / "missing")
    (missing / "player_stats.csv").unlink()
    with pytest.raises(ValueError, match=r"missing player_stats\.csv"):
        PreviewService(replace(settings, reference_package=missing))

    corrupt = _copy_package(synthetic_package.path, tmp_path / "corrupt")
    with (corrupt / "players.csv").open("a", encoding="utf-8") as handle:
        handle.write("\n")
    with pytest.raises(ValueError, match=r"players\.csv SHA-256 mismatch"):
        PreviewService(replace(settings, reference_package=corrupt))


async def test_startup_rejects_missing_season_and_oversized_cohort(
    settings: PreviewSettings,
    synthetic_package: SyntheticPackage,
) -> None:
    with pytest.raises(ValueError, match="no player rows.*2025"):
        PreviewService(replace(settings, season=2025))

    with pytest.raises(
        ValueError,
        match=rf"has {len(synthetic_package.cohort)} rows; maximum is 5",
    ):
        PreviewService(replace(settings, max_cohort_size=5))


async def test_startup_requires_exact_formula_reference_contract_version(
    settings: PreviewSettings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload, formula, formula_hash = service_module.load_formula_payload_snapshot()
    mismatched_formula = replace(formula, reference_contract_version=0)
    monkeypatch.setattr(
        service_module,
        "load_formula_payload_snapshot",
        lambda: (payload, mismatched_formula, formula_hash),
    )

    with pytest.raises(
        ValueError,
        match="requires reference contract version 0.*provides version 1",
    ):
        PreviewService(settings)


async def test_startup_rejects_published_attributes_that_drift_from_matching_formula(
    synthetic_package: SyntheticPackage,
    settings: PreviewSettings,
    tmp_path: Path,
) -> None:
    package = _copy_package(synthetic_package.path, tmp_path / "drifted-baseline")
    path = package / "player_attributes.csv"
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = list(reader.fieldnames or [])
        rows = list(reader)
    rows[0]["overall"] = "25" if rows[0]["overall"] != "25" else "26"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    refresh_manifest(package)

    with pytest.raises(ValueError, match="do not match shared-engine baseline"):
        PreviewService(replace(settings, reference_package=package))


async def test_package_with_a_different_published_formula_is_identified_but_recalculates_active(
    synthetic_package: SyntheticPackage,
    settings: PreviewSettings,
    tmp_path: Path,
) -> None:
    package = _copy_package(synthetic_package.path, tmp_path / "historical-formula")
    attributes_path = package / "player_attributes.csv"
    with attributes_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = list(reader.fieldnames or [])
        rows = list(reader)
    for row in rows:
        row["formulaVersion"] = "historical-formula"
    with attributes_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    manifest_path = package / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["formulaVersion"] = "historical-formula"
    manifest["formulaDocumentHash"] = "b" * 64
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    refresh_manifest(package)

    service = PreviewService(replace(settings, reference_package=package))
    context = service.context().model_dump(by_alias=True)
    assert context["referencePackage"]["publishedFormulaVersion"] == "historical-formula"
    assert context["referencePackage"]["publishedFormulaDocumentHash"] == "b" * 64
    assert context["formula"]["formulaVersion"] == synthetic_package.formula.formula_version
    assert context["formula"]["documentHash"] == synthetic_package.formula_hash


async def test_maximum_cohort_top_25_preview_meets_the_3000ms_budget(
    maximum_cohort_package: SyntheticPackage,
    maximum_cohort_settings: PreviewSettings,
) -> None:
    assert len(maximum_cohort_package.cohort) == maximum_cohort_settings.max_cohort_size
    assert maximum_cohort_settings.latency_budget_ms == 3000
    service = PreviewService(maximum_cohort_settings)
    transport = httpx2.ASGITransport(
        app=create_app(maximum_cohort_settings, service=service)
    )
    top_player_ids = [
        player.player_id for player in service.baseline(limit=25).players
    ]
    assert len(top_player_ids) == 25
    request = preview_request(
        maximum_cohort_package,
        top_player_ids,
        adjustments={
            "components": [
                {
                    "attribute": "overall",
                    "metric": "playerImpactEstimate",
                    "inverseDirection": True,
                }
            ]
        },
    )

    async with httpx2.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        started = perf_counter()
        response = await client.post("/api/v1/previews", json=request)
        wall_elapsed_ms = (perf_counter() - started) * 1000

    assert response.status_code == 200
    payload = response.json()
    assert payload["context"]["cohortSize"] == maximum_cohort_settings.max_cohort_size
    assert [player["playerId"] for player in payload["players"]] == top_player_ids
    assert payload["elapsedMs"] <= maximum_cohort_settings.latency_budget_ms
    assert wall_elapsed_ms <= maximum_cohort_settings.latency_budget_ms
