from __future__ import annotations

import csv
import hashlib
import json
import os
from copy import deepcopy
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path

import pandas as pd
import pytest
import yaml
from player_attribute_engine import FormulaContractError, load_formula_snapshot
from player_data_contracts.io import sha256_file
from player_data_contracts.reference import load_reference_contract
from reference_data_app import canonical, publication
from reference_data_app.adapters import NBA_PLAYERSTATS_V1_REQUIRED_COLUMNS
from reference_data_app.canonical import CanonicalBundle
from reference_data_app.cli import main
from reference_data_app.publication import CSV_FILENAMES, publish_reference_package
from reference_data_app.registration import RegistrationError, register_sources

CREATED_AT = datetime(2026, 7, 13, 14, 0, tzinfo=timezone.utc)


def _contract_row(
    contract: dict,
    filename: str,
    overrides: dict[str, object],
) -> dict[str, object]:
    return {
        column["name"]: overrides.get(column["name"])
        for column in contract["files"][filename]["columns"]
    }


def _bundle() -> CanonicalBundle:
    contract = load_reference_contract()
    player_id = "player_fixture"
    player_season_id = "playerSeason_fixture"
    identity = {
        "playerSeasonId": player_season_id,
        "playerId": player_id,
        "season": 2026,
    }
    return CanonicalBundle(
        players=[
            _contract_row(
                contract,
                "players.csv",
                {
                    "playerId": player_id,
                    "displayName": "José Example",
                    "heightInches": 78,
                    "weightPounds": 212,
                },
            )
        ],
        player_seasons=[
            _contract_row(
                contract,
                "player_seasons.csv",
                {**identity, "games": 72, "minutes": 2160.5},
            )
        ],
        player_stats=[
            _contract_row(
                contract,
                "player_stats.csv",
                {**identity, "points": 1234, "pointsPer36": 22.5},
            )
        ],
        player_advanced_stats=[
            _contract_row(
                contract,
                "player_advanced_stats.csv",
                {**identity, "usagePercentage": 0.287, "trueShootingPercentage": 0.621},
            )
        ],
        player_source_ids=[
            {
                "playerId": player_id,
                "sourceType": "nba_playerstats",
                "sourcePlayerId": "101",
            }
        ],
        sources=[
            {
                "sourceId": "nba:fixture",
                "sourceType": "nba_playerstats",
                "inputPath": "/outside/repository/playerstats.parquet",
                "originalFilename": "playerstats.parquet",
                "sha256": "a" * 64,
                "adapterVersion": 1,
                "upstreamVersion": None,
                "rowCount": 1,
                "processedAt": "2026-07-13T12:00:00Z",
                "licenseStatus": "test-fixture",
            }
        ],
        audit={
            "reconciliation": [
                {
                    "sourceType": "nba_playerstats",
                    "sourcePlayerId": "101",
                    "status": "anchor",
                    "rule": "primarySource",
                    "candidates": [],
                }
            ],
            "conflicts": [],
            "sourceContexts": [
                {
                    **identity,
                    "sourceId": "nba:fixture",
                    "sourceType": "nba_playerstats",
                    "sourcePlayerId": "101",
                    "sourceTeamId": 10,
                    "sourceTeamAbbreviation": "TST",
                    "teamCount": 1,
                }
            ],
        },
    )


def _cohort_bundle(seasons: tuple[int, ...] = (2025, 2026)) -> CanonicalBundle:
    contract = load_reference_contract()
    players: list[dict[str, object]] = []
    player_seasons: list[dict[str, object]] = []
    player_stats: list[dict[str, object]] = []
    player_advanced_stats: list[dict[str, object]] = []
    player_source_ids: list[dict[str, object]] = []
    source_contexts: list[dict[str, object]] = []
    for season in seasons:
        for index in range(2):
            player_id = f"player_{season}_{index}"
            player_season_id = f"playerSeason_{season}_{index}"
            identity = {
                "playerSeasonId": player_season_id,
                "playerId": player_id,
                "season": season,
            }
            games = 72 if index == 0 else 10
            minutes = 1800.0 if index == 0 else 200.0
            players.append(
                _contract_row(
                    contract,
                    "players.csv",
                    {"playerId": player_id, "displayName": f"Player {season} {index}"},
                )
            )
            player_seasons.append(
                _contract_row(
                    contract,
                    "player_seasons.csv",
                    {**identity, "games": games, "minutes": minutes},
                )
            )
            player_stats.append(
                _contract_row(
                    contract,
                    "player_stats.csv",
                    {
                        **identity,
                        "fieldGoalsAttempted": 500,
                        "twoPointersMade": 100 + index,
                        "twoPointersAttempted": 250,
                        "threePointersMade": 50 + index,
                        "threePointersAttempted": 150,
                        "freeThrowsMade": 70 + index,
                        "freeThrowsAttempted": 90,
                        "minutesPerGame": minutes / games,
                        "assistsPer36": 5.0 + index,
                        "pointsPer100": 105.0 + index,
                        "turnoversPer100": 3.0 - index / 10,
                        "stealsPer100": 1.5 + index / 10,
                        "blocksPer100": 0.5 + index / 10,
                        "twoPointAttemptFrequency": 0.55,
                        "threePointAttemptFrequency": 0.35,
                    },
                )
            )
            player_advanced_stats.append(
                _contract_row(
                    contract,
                    "player_advanced_stats.csv",
                    {
                        **identity,
                        "estimatedDefensiveRating": 110.0 - index,
                        "estimatedNetRating": 3.0 + index,
                        "assistPercentage": 0.20 + index / 100,
                        "assistTurnoverRatio": 2.0 + index / 10,
                        "assistRatio": 18.0 + index,
                        "offensiveReboundPercentage": 0.08 + index / 100,
                        "defensiveReboundPercentage": 0.20 + index / 100,
                        "estimatedTurnoverPercentage": 0.12 - index / 100,
                        "trueShootingPercentage": 0.58 + index / 100,
                        "usagePercentage": 0.24 + index / 100,
                        "playerImpactEstimate": 0.12 + index / 100,
                        "defensiveWinSharesPer36": 0.06 + index / 100,
                    },
                )
            )
            player_source_ids.append(
                {
                    "playerId": player_id,
                    "sourceType": "nba_playerstats",
                    "sourcePlayerId": f"{season}{index}",
                }
            )
            source_contexts.append(
                {
                    **identity,
                    "sourceId": "nba:fixture",
                    "sourceType": "nba_playerstats",
                    "sourcePlayerId": f"{season}{index}",
                    "sourceTeamId": 10,
                    "sourceTeamAbbreviation": "TST",
                    "teamCount": 1,
                }
            )
    return CanonicalBundle(
        players=players,
        player_seasons=player_seasons,
        player_stats=player_stats,
        player_advanced_stats=player_advanced_stats,
        player_source_ids=player_source_ids,
        sources=[
            {
                "sourceId": "nba:fixture",
                "sourceType": "nba_playerstats",
                "inputPath": "/outside/repository/playerstats.parquet",
                "originalFilename": "playerstats.parquet",
                "sha256": "a" * 64,
                "adapterVersion": 1,
                "upstreamVersion": None,
                "rowCount": len(player_seasons),
                "processedAt": "2026-07-13T12:00:00Z",
                "licenseStatus": "test-fixture",
            }
        ],
        audit={"reconciliation": [], "conflicts": [], "sourceContexts": source_contexts},
    )


def _publish_fixture(monkeypatch, output_path: Path, *, created_at: datetime = CREATED_AT) -> Path:
    bundle = _bundle()
    monkeypatch.setattr(publication, "normalize_registered_sources", lambda _config: bundle)
    return publish_reference_package({}, output_path, created_at=created_at)


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def _expected_content_hash(file_hashes: dict[str, str]) -> str:
    pairs = "\n".join(
        f"{filename}:{file_hashes[filename]}" for filename in sorted(file_hashes)
    )
    return hashlib.sha256(pairs.encode("utf-8")).hexdigest()


def test_publish_writes_golden_headers_values_and_empty_optionals(
    tmp_path: Path,
    monkeypatch,
) -> None:
    output_path = _publish_fixture(monkeypatch, tmp_path / "reference-v2")
    contract = load_reference_contract()

    assert {path.name for path in output_path.iterdir()} == {
        *CSV_FILENAMES,
        "audit.json",
        "manifest.json",
    }
    for filename in CSV_FILENAMES:
        headers, _rows = _read_csv(output_path / filename)
        assert headers == [
            column["name"] for column in contract["files"][filename]["columns"]
        ]
        content = (output_path / filename).read_text(encoding="utf-8")
        assert "nan" not in content.lower()
        assert "\r\n" not in content

    _headers, players = _read_csv(output_path / "players.csv")
    _headers, stats = _read_csv(output_path / "player_stats.csv")
    _headers, advanced = _read_csv(output_path / "player_advanced_stats.csv")
    _headers, attributes = _read_csv(output_path / "player_attributes.csv")
    _headers, sources = _read_csv(output_path / "sources.csv")
    assert players[0]["displayName"] == "José Example"
    assert players[0]["firstName"] == ""
    assert players[0]["birthDate"] == ""
    assert stats[0]["points"] == "1234"
    assert stats[0]["pointsPer36"] == "22.5"
    assert advanced[0]["usagePercentage"] == "0.287"
    assert attributes[0]["playerSeasonId"] == "playerSeason_fixture"
    assert attributes[0]["playerId"] == "player_fixture"
    assert attributes[0]["season"] == "2026"
    assert attributes[0]["overall"] == ""
    assert attributes[0]["formulaVersion"] == "1.0.0"
    assert sources[0]["upstreamVersion"] == ""
    assert "inputPath" not in sources[0]


def test_manifest_records_inputs_file_hashes_rows_and_content_hash(
    tmp_path: Path,
    monkeypatch,
) -> None:
    output_path = _publish_fixture(monkeypatch, tmp_path / "reference-v2")
    manifest = json.loads((output_path / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["manifestVersion"] == 1
    assert manifest["packageType"] == "reference"
    assert manifest["packageVersion"] == 2
    assert manifest["createdAt"] == "2026-07-13T14:00:00Z"
    assert manifest["contractVersions"] == {filename: 2 for filename in CSV_FILENAMES}
    _formula, formula_document_hash = load_formula_snapshot()
    assert manifest["formulaVersion"] == "1.0.0"
    assert manifest["formulaDocumentHash"] == formula_document_hash
    assert manifest["inputs"] == [
        {"sourceId": "nba:fixture", "sha256": "a" * 64, "adapterVersion": 1}
    ]
    file_hashes = {
        filename: sha256_file(output_path / filename)
        for filename in (*CSV_FILENAMES, "audit.json")
    }
    assert set(manifest["files"]) == set(file_hashes)
    assert manifest["files"]["players.csv"]["rowCount"] == 1
    assert manifest["files"]["player_attributes.csv"]["rowCount"] == 1
    assert manifest["files"]["audit.json"]["rowCount"] == 2
    for filename, digest in file_hashes.items():
        assert manifest["files"][filename]["sha256"] == digest
    assert manifest["contentHash"] == _expected_content_hash(file_hashes)


def test_repeat_publication_keeps_csv_audit_and_content_hash_deterministic(
    tmp_path: Path,
    monkeypatch,
) -> None:
    first = _publish_fixture(monkeypatch, tmp_path / "first", created_at=CREATED_AT)
    second = _publish_fixture(
        monkeypatch,
        tmp_path / "second",
        created_at=datetime(2026, 7, 13, 15, 0, tzinfo=timezone.utc),
    )

    for filename in (*CSV_FILENAMES, "audit.json"):
        assert (first / filename).read_bytes() == (second / filename).read_bytes()
    first_manifest = json.loads((first / "manifest.json").read_text(encoding="utf-8"))
    second_manifest = json.loads((second / "manifest.json").read_text(encoding="utf-8"))
    assert first_manifest["createdAt"] != second_manifest["createdAt"]
    assert first_manifest["files"] == second_manifest["files"]
    assert first_manifest["contentHash"] == second_manifest["contentHash"]


def test_attributes_evaluate_complete_season_cohorts_and_keep_ineligible_rows(
    tmp_path: Path,
    monkeypatch,
) -> None:
    bundle = _cohort_bundle()
    monkeypatch.setattr(publication, "normalize_registered_sources", lambda _config: bundle)
    calls: list[tuple[int, tuple[str, ...]]] = []
    evaluate = publication.evaluate_player_attributes

    def record_cohort(frame: pd.DataFrame, formula: object):
        calls.append(
            (
                int(frame["season"].iloc[0]),
                tuple(str(value) for value in frame["playerSeasonId"]),
            )
        )
        return evaluate(frame, formula)

    monkeypatch.setattr(publication, "evaluate_player_attributes", record_cohort)

    output_path = publish_reference_package(
        {}, tmp_path / "reference-v2", created_at=CREATED_AT
    )

    assert calls == [
        (2025, ("playerSeason_2025_0", "playerSeason_2025_1")),
        (2026, ("playerSeason_2026_0", "playerSeason_2026_1")),
    ]
    _headers, rows = _read_csv(output_path / "player_attributes.csv")
    assert [row["playerSeasonId"] for row in rows] == [
        "playerSeason_2025_0",
        "playerSeason_2025_1",
        "playerSeason_2026_0",
        "playerSeason_2026_1",
    ]
    by_id = {row["playerSeasonId"]: row for row in rows}
    for season in (2025, 2026):
        eligible = by_id[f"playerSeason_{season}_0"]
        ineligible = by_id[f"playerSeason_{season}_1"]
        assert eligible["overall"] != ""
        assert eligible["formulaVersion"] == "1.0.0"
        assert ineligible["overall"] == ""
        assert ineligible["impactPercentile"] == ""
        assert ineligible["talentTier"] == ""
        assert ineligible["formulaVersion"] == "1.0.0"


def test_unsupported_historical_seasons_keep_empty_attribute_rows(
    tmp_path: Path,
    monkeypatch,
) -> None:
    bundle = _cohort_bundle((2014, 2026))
    monkeypatch.setattr(publication, "normalize_registered_sources", lambda _config: bundle)
    evaluated_seasons: list[int] = []
    evaluate = publication.evaluate_player_attributes

    def record_supported_cohort(frame: pd.DataFrame, formula: object):
        evaluated_seasons.append(int(frame["season"].iloc[0]))
        return evaluate(frame, formula)

    monkeypatch.setattr(
        publication,
        "evaluate_player_attributes",
        record_supported_cohort,
    )

    output_path = publish_reference_package(
        {}, tmp_path / "reference-v2", created_at=CREATED_AT
    )

    assert evaluated_seasons == [2026]
    _headers, rows = _read_csv(output_path / "player_attributes.csv")
    by_id = {row["playerSeasonId"]: row for row in rows}
    calculated_fields = [
        field
        for field in load_formula_snapshot()[0].output_fields
        if field not in {"playerId", "formulaVersion"}
    ]
    for index in range(2):
        historical = by_id[f"playerSeason_2014_{index}"]
        assert historical["playerId"] == f"player_2014_{index}"
        assert historical["season"] == "2014"
        assert historical["formulaVersion"] == "1.0.0"
        assert all(historical[field] == "" for field in calculated_fields)
    assert by_id["playerSeason_2026_0"]["overall"] != ""


def test_evaluator_player_order_mismatch_is_rejected(
    tmp_path: Path,
    monkeypatch,
) -> None:
    bundle = _bundle()
    monkeypatch.setattr(publication, "normalize_registered_sources", lambda _config: bundle)
    evaluate = publication.evaluate_player_attributes

    def change_player_id(frame: pd.DataFrame, formula: object):
        batch = evaluate(frame, formula)
        batch.rows[0]["playerId"] = "different-player"
        return batch

    monkeypatch.setattr(publication, "evaluate_player_attributes", change_player_id)

    with pytest.raises(publication.PublicationError, match="playerId/order mismatch"):
        publish_reference_package({}, tmp_path / "reference-v2", created_at=CREATED_AT)


def test_formula_and_evaluation_failures_preserve_existing_package(
    tmp_path: Path,
    monkeypatch,
) -> None:
    output_path = tmp_path / "reference-v2"
    output_path.mkdir()
    marker = output_path / "old-package.txt"
    marker.write_text("keep me", encoding="utf-8")
    invalid_formula = tmp_path / "invalid-formula.json"
    invalid_formula.write_text("{", encoding="utf-8")

    with pytest.raises(FormulaContractError, match="Unable to load formula document"):
        publish_reference_package(
            {},
            output_path,
            formula_path=invalid_formula,
            created_at=CREATED_AT,
        )

    assert list(output_path.iterdir()) == [marker]

    monkeypatch.setattr(publication, "normalize_registered_sources", lambda _config: _bundle())

    def fail_evaluation(*_args, **_kwargs):
        raise RuntimeError("evaluation failure")

    monkeypatch.setattr(publication, "evaluate_player_attributes", fail_evaluation)
    with pytest.raises(RuntimeError, match="evaluation failure"):
        publish_reference_package({}, output_path, created_at=CREATED_AT)

    assert marker.read_text(encoding="utf-8") == "keep me"
    assert list(output_path.iterdir()) == [marker]
    assert not list(tmp_path.glob(".reference-v2.tmp-*"))
    assert not list(tmp_path.glob(".reference-v2.backup-*"))


def test_validation_failure_preserves_old_package_and_cleans_staging(
    tmp_path: Path,
    monkeypatch,
) -> None:
    output_path = tmp_path / "reference-v2"
    output_path.mkdir()
    marker = output_path / "old-package.txt"
    marker.write_text("keep me", encoding="utf-8")
    monkeypatch.setattr(publication, "normalize_registered_sources", lambda _config: _bundle())

    def fail_validation(*_args, **_kwargs) -> None:
        raise RuntimeError("contract failure")

    monkeypatch.setattr(publication, "validate_reference_package", fail_validation)

    with pytest.raises(RuntimeError, match="contract failure"):
        publish_reference_package({}, output_path, created_at=CREATED_AT)

    assert marker.read_text(encoding="utf-8") == "keep me"
    assert list(output_path.iterdir()) == [marker]
    assert not list(tmp_path.glob(".reference-v2.tmp-*"))
    assert not list(tmp_path.glob(".reference-v2.backup-*"))


def test_failed_final_replace_restores_existing_package_and_cleans_backup(
    tmp_path: Path,
    monkeypatch,
) -> None:
    output_path = tmp_path / "reference-v2"
    output_path.mkdir()
    marker = output_path / "old-package.txt"
    marker.write_text("keep me", encoding="utf-8")
    monkeypatch.setattr(publication, "normalize_registered_sources", lambda _config: _bundle())
    real_replace = os.replace

    def fail_stage_replace(source, destination) -> None:
        if Path(source).name.startswith(".reference-v2.tmp-") and Path(destination) == output_path:
            raise OSError("replace failure")
        real_replace(source, destination)

    monkeypatch.setattr(publication.os, "replace", fail_stage_replace)

    with pytest.raises(OSError, match="replace failure"):
        publish_reference_package({}, output_path, created_at=CREATED_AT)

    assert marker.read_text(encoding="utf-8") == "keep me"
    assert list(output_path.iterdir()) == [marker]
    assert not list(tmp_path.glob(".reference-v2.tmp-*"))
    assert not list(tmp_path.glob(".reference-v2.backup-*"))


def _nba_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        column: 0 for column in NBA_PLAYERSTATS_V1_REQUIRED_COLUMNS
    }
    row.update(
        {
            "player_id": 101,
            "player_name": "CLI Player",
            "team_id": 10,
            "team_abbreviation": "TST",
            "team_count": 1,
            "year": 2026,
            "age": 26,
            "gp": 72,
            "w": 45,
            "l": 27,
            "min": 2160,
            "player_height_inches": 78,
            "player_weight": "212",
        }
    )
    row.update(overrides)
    return row


def _registered_nba_config(
    tmp_path: Path,
    reference_config: dict,
) -> tuple[dict, Path]:
    registry_path = tmp_path / "registry" / "sources.json"
    source_path = tmp_path / "playerstats.parquet"
    pd.DataFrame([_nba_row()]).to_parquet(source_path, index=False)
    register_sources(
        [source_path],
        registry_path=registry_path,
        source_type="nba_playerstats",
        license_status="test-fixture",
        processed_at=CREATED_AT,
    )
    config = deepcopy(reference_config)
    config["_meta"] = {"project_root": str(tmp_path)}
    config["paths"]["source_registry"] = str(registry_path)
    config["paths"]["reference_package_dir"] = str(tmp_path / "configured-package")
    return config, source_path


def test_publish_cli_builds_package_from_synthetic_registered_parquet(
    tmp_path: Path,
    reference_config: dict,
    capsys,
) -> None:
    config, _source_path = _registered_nba_config(tmp_path, reference_config)
    config_path = tmp_path / "reference.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    output_path = tmp_path / "cli-package"
    formula_path = tmp_path / "player-attributes.json"
    formula_bytes = (
        files("player_attribute_engine")
        .joinpath("formulas/player-attributes-v1.json")
        .read_bytes()
    )
    formula_path.write_bytes(formula_bytes + b"\n")

    result = main(
        [
            "--config",
            str(config_path),
            "publish",
            "--output",
            str(output_path),
            "--formula",
            str(formula_path),
        ]
    )

    assert result == 0
    assert f"Published normalized reference package to {output_path}." in capsys.readouterr().out
    assert {path.name for path in output_path.iterdir()} == {
        *CSV_FILENAMES,
        "audit.json",
        "manifest.json",
    }
    manifest = json.loads((output_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["formulaVersion"] == "1.0.0"
    assert manifest["formulaDocumentHash"] == sha256_file(formula_path)


def test_publish_rejects_replaced_registered_source_and_preserves_existing_package(
    tmp_path: Path,
    reference_config: dict,
) -> None:
    config, source_path = _registered_nba_config(tmp_path, reference_config)
    output_path = tmp_path / "reference-v2"
    output_path.mkdir()
    marker = output_path / "old-package.txt"
    marker.write_text("keep me", encoding="utf-8")
    pd.DataFrame([_nba_row(player_name="Replacement Player")]).to_parquet(
        source_path,
        index=False,
    )

    with pytest.raises(RegistrationError) as error:
        publish_reference_package(config, output_path, created_at=CREATED_AT)

    message = str(error.value)
    assert str(source_path) in message
    assert "adapter nba_playerstats v1" in message
    assert "source ID 'nba_playerstats:playerstats'" in message
    assert "SHA-256 changed" in message
    assert "rebuild its local registration before publishing" in message
    assert marker.read_text(encoding="utf-8") == "keep me"
    assert list(output_path.iterdir()) == [marker]
    assert not list(tmp_path.glob(".reference-v2.tmp-*"))
    assert not list(tmp_path.glob(".reference-v2.backup-*"))


def test_publish_rechecks_source_after_normalization(
    tmp_path: Path,
    reference_config: dict,
    monkeypatch,
) -> None:
    config, source_path = _registered_nba_config(tmp_path, reference_config)
    output_path = tmp_path / "reference-v2"
    output_path.mkdir()
    marker = output_path / "old-package.txt"
    marker.write_text("keep me", encoding="utf-8")
    normalize_source = canonical.normalize_source

    def normalize_then_replace(*args, **kwargs):
        normalized = normalize_source(*args, **kwargs)
        pd.DataFrame([_nba_row(player_name="Changed During Read")]).to_parquet(
            source_path,
            index=False,
        )
        return normalized

    monkeypatch.setattr(canonical, "normalize_source", normalize_then_replace)

    with pytest.raises(RegistrationError, match="SHA-256 changed"):
        publish_reference_package(config, output_path, created_at=CREATED_AT)

    assert marker.read_text(encoding="utf-8") == "keep me"
    assert list(output_path.iterdir()) == [marker]
    assert not list(tmp_path.glob(".reference-v2.tmp-*"))
    assert not list(tmp_path.glob(".reference-v2.backup-*"))
