from __future__ import annotations

import csv
import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx2
import pandas as pd
import pytest
from formula_preview_api import PreviewService, PreviewSettings, create_app
from player_attribute_engine import (
    EvaluationBatch,
    FormulaDocument,
    evaluate_player_attributes,
    load_formula_payload_snapshot,
)
from player_data_contracts import load_reference_contract
from player_data_contracts.io import sha256_file
from player_data_contracts.package import content_hash

SEASON = 2026


@dataclass(frozen=True)
class SyntheticPackage:
    path: Path
    cohort: pd.DataFrame
    evaluation: EvaluationBatch
    formula_payload: dict[str, Any]
    formula: FormulaDocument
    formula_hash: str
    content_hash: str

    @property
    def rows_by_player(self) -> dict[str, dict[str, Any]]:
        return {str(row["playerId"]): row for row in self.evaluation.rows}

    @property
    def explanations_by_player(self) -> dict[str, dict[str, Any]]:
        return {
            str(explanation["playerId"]): explanation
            for explanation in self.evaluation.explanations
        }


def _contract_row(
    contract: Mapping[str, Any],
    filename: str,
    values: Mapping[str, object],
) -> dict[str, object]:
    return {
        str(column["name"]): values.get(str(column["name"]))
        for column in contract["files"][filename]["columns"]
    }


def _base_player(
    player_id: str,
    display_name: str,
    ordinal: int,
    **overrides: object,
) -> dict[str, object]:
    score = float(ordinal)
    cycle = float(ordinal % 100)
    row: dict[str, object] = {
        "playerId": player_id,
        "displayName": display_name,
        "season": SEASON,
        "games": 60,
        "minutes": 1200.0 + score,
        "minutesPerGame": 20.0 + cycle / 20.0,
        "fieldGoalsAttempted": 500.0,
        "twoPointersMade": 100.0 + cycle / 2.0,
        "twoPointersAttempted": 300.0,
        "threePointersMade": 50.0 + cycle / 4.0,
        "threePointersAttempted": 200.0,
        "freeThrowsMade": 70.0 + cycle / 5.0,
        "freeThrowsAttempted": 100.0,
        "twoPointAttemptFrequency": 0.45 + cycle / 1000.0,
        "threePointAttemptFrequency": 0.30 + cycle / 1500.0,
        "pointsPer100": 90.0 + cycle / 2.0,
        "usagePercentage": 0.18 + cycle / 1000.0,
        "trueShootingPercentage": 0.48 + cycle / 2000.0,
        "assistPercentage": 0.10 + cycle / 1000.0,
        "assistsPer36": 2.0 + cycle / 20.0,
        "assistRatio": 10.0 + cycle / 10.0,
        "assistTurnoverRatio": 1.0 + cycle / 50.0,
        "estimatedTurnoverPercentage": 0.18 - cycle / 2000.0,
        "turnoversPer100": 5.0 - cycle / 100.0,
        "offensiveReboundPercentage": 0.03 + cycle / 2000.0,
        "defensiveReboundPercentage": 0.10 + cycle / 1000.0,
        "stealsPer100": 0.5 + cycle / 100.0,
        "blocksPer100": 0.2 + cycle / 200.0,
        "estimatedDefensiveRating": 120.0 - cycle / 5.0,
        "defensiveWinSharesPer36": 0.02 + cycle / 5000.0,
        "playerImpactEstimate": 0.03 + cycle / 1000.0,
        "estimatedNetRating": -8.0 + cycle / 5.0,
    }
    row.update(overrides)
    return row


def representative_players() -> list[dict[str, object]]:
    return [
        _base_player("player-star", "Avery Star", 95),
        _base_player("player-starter", "Casey Starter", 72),
        _base_player(
            "player-impact",
            "Imani Impact",
            50,
            playerImpactEstimate=0.30,
            estimatedNetRating=18.0,
            pointsPer100=91.0,
        ),
        _base_player(
            "player-volume",
            "Victor Volume",
            45,
            playerImpactEstimate=0.035,
            estimatedNetRating=-3.0,
            pointsPer100=150.0,
            usagePercentage=0.39,
        ),
        _base_player(
            "player-shooter",
            "José Example",
            38,
            threePointersMade=180.0,
            threePointAttemptFrequency=0.75,
        ),
        _base_player(
            "player-security",
            "Bailey Secure",
            35,
            estimatedTurnoverPercentage=0.03,
            assistTurnoverRatio=8.0,
            turnoversPer100=0.5,
        ),
        _base_player("player-tie-a", "Taylor Tie A", 28),
        _base_player("player-tie-b", "Taylor Tie B", 28),
        _base_player("player-role", "Riley Role", 20),
        _base_player("player-pinned", "Parker Pin", 4),
        _base_player(
            "player-low-minute",
            "Logan Limited",
            80,
            games=19,
            minutes=499.0,
        ),
        _base_player(
            "player-missing-impact",
            "Morgan Missing",
            65,
            playerImpactEstimate=None,
        ),
    ]


def maximum_cohort_players(size: int) -> list[dict[str, object]]:
    return [
        _base_player(
            f"performance-{index:04d}",
            f"Performance Player {index:04d}",
            index,
        )
        for index in range(1, size + 1)
    ]


def _write_csv(path: Path, headers: Sequence[str], rows: Sequence[Mapping[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _package_tables(
    players: Sequence[Mapping[str, object]],
    contract: Mapping[str, Any],
    formula: FormulaDocument,
) -> tuple[dict[str, list[dict[str, object]]], pd.DataFrame, EvaluationBatch]:
    player_rows: list[dict[str, object]] = []
    season_rows: list[dict[str, object]] = []
    stats_rows: list[dict[str, object]] = []
    advanced_rows: list[dict[str, object]] = []
    source_id_rows: list[dict[str, object]] = []
    cohort_rows: list[dict[str, object]] = []

    for raw in players:
        player_id = str(raw["playerId"])
        player_season_id = f"season-{player_id}"
        identity = {
            "playerSeasonId": player_season_id,
            "playerId": player_id,
            "season": SEASON,
        }
        player_rows.append(
            _contract_row(
                contract,
                "players.csv",
                {
                    "playerId": player_id,
                    "displayName": raw["displayName"],
                    "firstName": str(raw["displayName"]).split()[0],
                    "lastName": str(raw["displayName"]).split()[-1],
                },
            )
        )
        season_values = {**raw, **identity}
        season_rows.append(
            _contract_row(contract, "player_seasons.csv", season_values)
        )
        stats_rows.append(_contract_row(contract, "player_stats.csv", season_values))
        advanced_rows.append(
            _contract_row(contract, "player_advanced_stats.csv", season_values)
        )
        source_id_rows.append(
            _contract_row(
                contract,
                "player_source_ids.csv",
                {
                    "playerId": player_id,
                    "sourceType": "synthetic",
                    "sourcePlayerId": f"upstream-{player_id}",
                },
            )
        )
        cohort_rows.append({**raw, **identity})

    cohort = pd.DataFrame(cohort_rows).sort_values("playerId", kind="stable").reset_index(
        drop=True
    )
    evaluation = evaluate_player_attributes(cohort, formula)
    attributes: list[dict[str, object]] = []
    season_ids = {
        str(row["playerId"]): str(row["playerSeasonId"]) for row in cohort_rows
    }
    for evaluated in evaluation.rows:
        player_id = str(evaluated["playerId"])
        attributes.append(
            _contract_row(
                contract,
                "player_attributes.csv",
                {
                    **evaluated,
                    "playerSeasonId": season_ids[player_id],
                    "season": SEASON,
                },
            )
        )

    sources = [
        _contract_row(
            contract,
            "sources.csv",
            {
                "sourceId": "synthetic:test",
                "sourceType": "synthetic",
                "originalFilename": "synthetic-test.parquet",
                "sha256": "a" * 64,
                "adapterVersion": 1,
                "upstreamVersion": "test-v1",
                "rowCount": len(players),
                "processedAt": "2026-07-13T12:00:00Z",
                "licenseStatus": "test-only",
            },
        )
    ]
    tables = {
        "players.csv": player_rows,
        "player_seasons.csv": season_rows,
        "player_stats.csv": stats_rows,
        "player_advanced_stats.csv": advanced_rows,
        "player_attributes.csv": attributes,
        "player_source_ids.csv": source_id_rows,
        "sources.csv": sources,
    }
    return tables, cohort, evaluation


def refresh_manifest(path: Path) -> dict[str, Any]:
    manifest_path = path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    hashes = {filename: sha256_file(path / filename) for filename in manifest["files"]}
    for filename, digest in hashes.items():
        manifest["files"][filename]["sha256"] = digest
        if filename.endswith(".csv"):
            with (path / filename).open(encoding="utf-8", newline="") as handle:
                manifest["files"][filename]["rowCount"] = sum(1 for _ in handle) - 1
    manifest["contentHash"] = content_hash(hashes)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def build_reference_package(
    path: Path,
    players: Sequence[Mapping[str, object]],
) -> SyntheticPackage:
    payload, formula, formula_hash = load_formula_payload_snapshot()
    contract = load_reference_contract(2)
    tables, cohort, evaluation = _package_tables(players, contract, formula)
    path.mkdir(parents=True)
    for filename, rows in tables.items():
        headers = [
            str(column["name"]) for column in contract["files"][filename]["columns"]
        ]
        _write_csv(path / filename, headers, rows)

    audit = {"conflicts": [], "reconciliation": [], "sourceContexts": []}
    (path / "audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    data_filenames = (*tables, "audit.json")
    hashes = {filename: sha256_file(path / filename) for filename in data_filenames}
    manifest = {
        "manifestVersion": 1,
        "packageType": "reference",
        "packageVersion": 2,
        "createdAt": "2026-07-13T12:00:00Z",
        "formulaVersion": formula.formula_version,
        "formulaDocumentHash": formula_hash,
        "contractVersions": dict.fromkeys(tables, 2),
        "inputs": [],
        "files": {
            filename: {
                "rowCount": len(tables[filename]) if filename in tables else 0,
                "sha256": hashes[filename],
            }
            for filename in data_filenames
        },
        "contentHash": content_hash(hashes),
    }
    (path / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return SyntheticPackage(
        path=path,
        cohort=cohort,
        evaluation=evaluation,
        formula_payload=payload,
        formula=formula,
        formula_hash=formula_hash,
        content_hash=str(manifest["contentHash"]),
    )


def file_hashes(path: Path) -> dict[str, str]:
    return {
        item.name: hashlib.sha256(item.read_bytes()).hexdigest()
        for item in sorted(path.iterdir())
        if item.is_file()
    }


def preview_request(
    package: SyntheticPackage,
    player_ids: Sequence[str],
    *,
    adjustments: Mapping[str, object] | None = None,
) -> dict[str, object]:
    return {
        "apiVersion": "1",
        "referencePackageHash": package.content_hash,
        "formulaVersion": package.formula.formula_version,
        "formulaDocumentHash": package.formula_hash,
        "season": SEASON,
        "selectedPlayerIds": list(player_ids),
        "adjustments": dict(adjustments or {}),
    }


@pytest.fixture(scope="session")
def synthetic_package(tmp_path_factory: pytest.TempPathFactory) -> SyntheticPackage:
    return build_reference_package(
        tmp_path_factory.mktemp("preview-api") / "reference-v2",
        representative_players(),
    )


@pytest.fixture(scope="session")
def settings(synthetic_package: SyntheticPackage) -> PreviewSettings:
    return PreviewSettings(
        reference_package=synthetic_package.path,
        season=SEASON,
        default_sample_size=3,
        max_pinned_players=5,
        max_selected_players=5,
        max_search_results=8,
        max_cohort_size=1000,
        latency_budget_ms=3000,
    )


@pytest.fixture(scope="session")
def service(settings: PreviewSettings) -> PreviewService:
    return PreviewService(settings)


@pytest.fixture
async def client(
    settings: PreviewSettings,
    service: PreviewService,
) -> httpx2.AsyncClient:
    transport = httpx2.ASGITransport(app=create_app(settings, service=service))
    async with httpx2.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as active:
        yield active


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def request_payload(
    synthetic_package: SyntheticPackage,
) -> Callable[[Sequence[str], Mapping[str, object] | None], dict[str, object]]:
    def build(
        player_ids: Sequence[str],
        adjustments: Mapping[str, object] | None = None,
    ) -> dict[str, object]:
        return preview_request(
            synthetic_package,
            player_ids,
            adjustments=adjustments,
        )

    return build


@pytest.fixture(scope="session")
def maximum_cohort_package(tmp_path_factory: pytest.TempPathFactory) -> SyntheticPackage:
    return build_reference_package(
        tmp_path_factory.mktemp("preview-api-performance") / "reference-v2",
        maximum_cohort_players(1000),
    )


@pytest.fixture(scope="session")
def maximum_cohort_settings(
    maximum_cohort_package: SyntheticPackage,
) -> PreviewSettings:
    return PreviewSettings(
        reference_package=maximum_cohort_package.path,
        season=SEASON,
        default_sample_size=25,
        max_pinned_players=25,
        max_selected_players=25,
        max_search_results=20,
        max_cohort_size=1000,
        latency_budget_ms=3000,
    )
