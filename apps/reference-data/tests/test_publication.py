from __future__ import annotations

import csv
import hashlib
import json
import os
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest
import yaml
from player_data_contracts.io import sha256_file
from player_data_contracts.reference import load_reference_contract
from reference_data_app import publication
from reference_data_app.adapters import NBA_PLAYERSTATS_V1_REQUIRED_COLUMNS
from reference_data_app.canonical import CanonicalBundle
from reference_data_app.cli import main
from reference_data_app.publication import CSV_FILENAMES, publish_reference_package
from reference_data_app.registration import register_sources

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
    output_path = _publish_fixture(monkeypatch, tmp_path / "reference-v1")
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
    _headers, sources = _read_csv(output_path / "sources.csv")
    assert players[0]["displayName"] == "José Example"
    assert players[0]["firstName"] == ""
    assert players[0]["birthDate"] == ""
    assert stats[0]["points"] == "1234"
    assert stats[0]["pointsPer36"] == "22.5"
    assert advanced[0]["usagePercentage"] == "0.287"
    assert sources[0]["upstreamVersion"] == ""
    assert "inputPath" not in sources[0]


def test_manifest_records_inputs_file_hashes_rows_and_content_hash(
    tmp_path: Path,
    monkeypatch,
) -> None:
    output_path = _publish_fixture(monkeypatch, tmp_path / "reference-v1")
    manifest = json.loads((output_path / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["manifestVersion"] == 1
    assert manifest["packageType"] == "reference"
    assert manifest["packageVersion"] == 1
    assert manifest["createdAt"] == "2026-07-13T14:00:00Z"
    assert manifest["contractVersions"] == {filename: 1 for filename in CSV_FILENAMES}
    assert manifest["inputs"] == [
        {"sourceId": "nba:fixture", "sha256": "a" * 64, "adapterVersion": 1}
    ]
    file_hashes = {
        filename: sha256_file(output_path / filename)
        for filename in (*CSV_FILENAMES, "audit.json")
    }
    assert set(manifest["files"]) == set(file_hashes)
    assert manifest["files"]["players.csv"]["rowCount"] == 1
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


def test_validation_failure_preserves_old_package_and_cleans_staging(
    tmp_path: Path,
    monkeypatch,
) -> None:
    output_path = tmp_path / "reference-v1"
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
    assert not list(tmp_path.glob(".reference-v1.tmp-*"))
    assert not list(tmp_path.glob(".reference-v1.backup-*"))


def test_failed_final_replace_restores_existing_package_and_cleans_backup(
    tmp_path: Path,
    monkeypatch,
) -> None:
    output_path = tmp_path / "reference-v1"
    output_path.mkdir()
    marker = output_path / "old-package.txt"
    marker.write_text("keep me", encoding="utf-8")
    monkeypatch.setattr(publication, "normalize_registered_sources", lambda _config: _bundle())
    real_replace = os.replace

    def fail_stage_replace(source, destination) -> None:
        if Path(source).name.startswith(".reference-v1.tmp-") and Path(destination) == output_path:
            raise OSError("replace failure")
        real_replace(source, destination)

    monkeypatch.setattr(publication.os, "replace", fail_stage_replace)

    with pytest.raises(OSError, match="replace failure"):
        publish_reference_package({}, output_path, created_at=CREATED_AT)

    assert marker.read_text(encoding="utf-8") == "keep me"
    assert list(output_path.iterdir()) == [marker]
    assert not list(tmp_path.glob(".reference-v1.tmp-*"))
    assert not list(tmp_path.glob(".reference-v1.backup-*"))


def _nba_row() -> dict[str, object]:
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
    return row


def test_publish_cli_builds_package_from_synthetic_registered_parquet(
    tmp_path: Path,
    reference_config: dict,
    capsys,
) -> None:
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
    config["paths"]["source_registry"] = str(registry_path)
    config["paths"]["reference_package_dir"] = str(tmp_path / "configured-package")
    config_path = tmp_path / "reference.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    output_path = tmp_path / "cli-package"

    result = main(
        [
            "--config",
            str(config_path),
            "publish",
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    assert f"Published normalized reference package to {output_path}." in capsys.readouterr().out
    assert {path.name for path in output_path.iterdir()} == {
        *CSV_FILENAMES,
        "audit.json",
        "manifest.json",
    }
