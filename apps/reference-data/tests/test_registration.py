from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest
from reference_data_app.adapters import (
    ESPN_PLAYER_DETAILS_V1_REQUIRED_COLUMNS,
    NBA_PLAYERSTATS_V1_REQUIRED_COLUMNS,
    AdapterValidationError,
)
from reference_data_app.cli import main
from reference_data_app.registration import (
    RegistrationError,
    load_registered_sources,
    register_sources,
)

FIRST_TIMESTAMP = datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc)
LATER_TIMESTAMP = datetime(2026, 7, 13, 13, 0, tzinfo=timezone.utc)


def _write_parquet(path: Path, rows: list[dict[str, object]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(path, index=False)
    return path


def _nba_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        column: 0 for column in NBA_PLAYERSTATS_V1_REQUIRED_COLUMNS
    }
    row.update(
        {
            "player_id": 101,
            "player_name": "Sample Player",
            "team_id": 10,
            "team_abbreviation": "TST",
            "year": 2026,
            "team_count": 1,
        }
    )
    row.update(overrides)
    return row


def _espn_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        column: "sample" for column in ESPN_PLAYER_DETAILS_V1_REQUIRED_COLUMNS
    }
    row.update({"id": "espn-101", "displayName": "Sample Player"})
    row.update(overrides)
    return row


def test_registers_supported_sources_with_provenance_without_copying(tmp_path: Path) -> None:
    source_dir = tmp_path / "outside-inputs"
    registry_path = tmp_path / "state" / "sources.json"
    nba_path = _write_parquet(source_dir / "NBA Player Stats.parquet", [_nba_row(), _nba_row()])
    espn_path = _write_parquet(source_dir / "espn-details.parquet", [_espn_row()])

    nba_sources = register_sources(
        [nba_path],
        registry_path=registry_path,
        source_type="nba_playerstats",
        upstream_version="snapshot-2026-07-12",
        license_status="unverified",
        processed_at=FIRST_TIMESTAMP,
    )
    espn_sources = register_sources(
        [espn_path],
        registry_path=registry_path,
        source_type="espn_player_details",
        processed_at=FIRST_TIMESTAMP,
    )

    nba = nba_sources[0]
    assert nba.source_id == "nba_playerstats:nba-player-stats"
    assert nba.original_filename == "NBA Player Stats.parquet"
    assert nba.input_path == str(nba_path.resolve())
    assert len(nba.sha256) == 64
    assert nba.adapter_version == 1
    assert nba.row_count == 2
    assert nba.processed_at == "2026-07-13T12:00:00Z"
    assert nba.upstream_version == "snapshot-2026-07-12"
    assert nba.license_status == "unverified"
    assert espn_sources[0].source_id == "espn_player_details:espn-details"
    assert espn_sources[0].license_status == "unknown"

    registered = load_registered_sources(registry_path)
    assert [source.source_id for source in registered] == [
        "espn_player_details:espn-details",
        "nba_playerstats:nba-player-stats",
    ]
    assert not list((tmp_path / "state").rglob("*.parquet"))
    assert nba_path.exists()
    assert espn_path.exists()


def test_registers_multiple_paths_and_sorts_registry_deterministically(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.json"
    second = _write_parquet(tmp_path / "z-source.parquet", [_espn_row(id="2")])
    first = _write_parquet(tmp_path / "a-source.parquet", [_espn_row(id="1")])

    register_sources(
        [second, first],
        registry_path=registry_path,
        source_type="espn_player_details",
        processed_at=FIRST_TIMESTAMP,
    )

    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    assert payload["registryVersion"] == 1
    assert [source["sourceId"] for source in payload["sources"]] == [
        "espn_player_details:a-source",
        "espn_player_details:z-source",
    ]
    assert {source["processedAt"] for source in payload["sources"]} == {
        "2026-07-13T12:00:00Z"
    }


def test_identical_registration_is_idempotent_and_preserves_timestamp(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.json"
    source_path = _write_parquet(tmp_path / "players.parquet", [_espn_row()])
    original = register_sources(
        [source_path],
        registry_path=registry_path,
        source_type="espn_player_details",
        processed_at=FIRST_TIMESTAMP,
    )[0]
    original_bytes = registry_path.read_bytes()

    duplicate = register_sources(
        [source_path],
        registry_path=registry_path,
        source_type="espn_player_details",
        processed_at=LATER_TIMESTAMP,
    )[0]

    assert duplicate == original
    assert duplicate.processed_at == "2026-07-13T12:00:00Z"
    assert registry_path.read_bytes() == original_bytes


def test_changed_content_reports_hash_conflict_without_rewriting_registry(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.json"
    source_path = _write_parquet(tmp_path / "players.parquet", [_espn_row()])
    register_sources(
        [source_path],
        registry_path=registry_path,
        source_type="espn_player_details",
        processed_at=FIRST_TIMESTAMP,
    )
    original_registry = registry_path.read_bytes()
    _write_parquet(source_path, [_espn_row(displayName="Changed Player")])

    with pytest.raises(RegistrationError) as error:
        register_sources(
            [source_path],
            registry_path=registry_path,
            source_type="espn_player_details",
            processed_at=LATER_TIMESTAMP,
        )

    message = str(error.value)
    assert str(source_path) in message
    assert "adapter espn_player_details v1" in message
    assert "different content" in message
    assert registry_path.read_bytes() == original_registry


def test_conflicting_explicit_source_id_is_reported(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.json"
    first = _write_parquet(tmp_path / "first.parquet", [_espn_row()])
    second = _write_parquet(tmp_path / "second.parquet", [_espn_row()])
    register_sources(
        [first],
        registry_path=registry_path,
        source_type="espn_player_details",
        source_id="espn:details",
        processed_at=FIRST_TIMESTAMP,
    )

    with pytest.raises(RegistrationError, match="conflicts with the existing registration"):
        register_sources(
            [second],
            registry_path=registry_path,
            source_type="espn_player_details",
            source_id="espn:details",
            processed_at=LATER_TIMESTAMP,
        )


def test_missing_columns_error_names_file_adapter_and_fields(tmp_path: Path) -> None:
    source_path = _write_parquet(tmp_path / "details.parquet", [{"id": "espn-101"}])

    with pytest.raises(AdapterValidationError) as error:
        register_sources(
            [source_path],
            registry_path=tmp_path / "registry.json",
            source_type="espn_player_details",
            processed_at=FIRST_TIMESTAMP,
        )

    message = str(error.value)
    assert str(source_path) in message
    assert "adapter espn_player_details v1" in message
    assert "missing required fields" in message
    assert "displayName" in message


def test_invalid_parquet_error_names_file_and_adapter(tmp_path: Path) -> None:
    source_path = tmp_path / "not-parquet.parquet"
    source_path.write_text("not parquet", encoding="utf-8")

    with pytest.raises(AdapterValidationError) as error:
        register_sources(
            [source_path],
            registry_path=tmp_path / "registry.json",
            source_type="espn_player_details",
            processed_at=FIRST_TIMESTAMP,
        )

    message = str(error.value)
    assert str(source_path) in message
    assert "adapter espn_player_details v1" in message
    assert "unreadable Parquet" in message


def test_unsupported_adapter_version_names_file_adapter_and_supported_version(
    tmp_path: Path,
) -> None:
    source_path = _write_parquet(tmp_path / "details.parquet", [_espn_row()])

    with pytest.raises(AdapterValidationError) as error:
        register_sources(
            [source_path],
            registry_path=tmp_path / "registry.json",
            source_type="espn_player_details",
            adapter_version=2,
            processed_at=FIRST_TIMESTAMP,
        )

    message = str(error.value)
    assert str(source_path) in message
    assert "adapter espn_player_details v2" in message
    assert "unsupported adapter schema version" in message
    assert "supported versions: 1" in message


def test_batch_validation_failure_does_not_create_partial_registry(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.json"
    valid = _write_parquet(tmp_path / "valid.parquet", [_espn_row()])
    missing = tmp_path / "missing.parquet"

    with pytest.raises(AdapterValidationError, match="file does not exist"):
        register_sources(
            [valid, missing],
            registry_path=registry_path,
            source_type="espn_player_details",
            processed_at=FIRST_TIMESTAMP,
        )

    assert not registry_path.exists()


def test_explicit_source_id_requires_exactly_one_path(tmp_path: Path) -> None:
    first = _write_parquet(tmp_path / "first.parquet", [_espn_row()])
    second = _write_parquet(tmp_path / "second.parquet", [_espn_row()])

    with pytest.raises(RegistrationError, match="exactly one path"):
        register_sources(
            [first, second],
            registry_path=tmp_path / "registry.json",
            source_type="espn_player_details",
            source_id="espn:details",
            processed_at=FIRST_TIMESTAMP,
        )


def test_register_cli_accepts_local_path_and_metadata(tmp_path: Path, capsys) -> None:
    registry_path = tmp_path / "registry" / "sources.json"
    config_path = tmp_path / "reference.yaml"
    config_path.write_text(
        f"paths:\n  source_registry: {registry_path}\n",
        encoding="utf-8",
    )
    source_path = _write_parquet(tmp_path / "details.parquet", [_espn_row()])

    result = main(
        [
            "--config",
            str(config_path),
            "register",
            "--source-type",
            "espn_player_details",
            "--source-id",
            "espn:2026",
            "--upstream-version",
            "2026-07",
            "--license-status",
            "review-required",
            str(source_path),
        ]
    )

    assert result == 0
    assert "Registered or verified 1 local reference source(s)." in capsys.readouterr().out
    registered = load_registered_sources(registry_path)
    assert registered[0].source_id == "espn:2026"
    assert registered[0].upstream_version == "2026-07"
    assert registered[0].license_status == "review-required"
