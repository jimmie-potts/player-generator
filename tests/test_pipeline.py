from __future__ import annotations

import pandas as pd
import pytest

from player_generator.pipeline import (
    REFERENCE_SEASONS_FILE,
    REFERENCE_SNAPSHOT_FILE,
    _read_records_json,
    _write_records_json,
)


def test_reference_outputs_use_json_filenames() -> None:
    assert REFERENCE_SEASONS_FILE == "player_seasons_reference.json"
    assert REFERENCE_SNAPSHOT_FILE == "reference_players.json"


def test_reference_records_json_round_trip(tmp_path) -> None:
    path = tmp_path / "reference.json"
    source = pd.DataFrame(
        [
            {
                "season_year": 2026,
                "sourcePlayerId": 101,
                "sourcePlayerName": "José Example",
                "impactPercentile": 0.99468085106383,
                "draftYear": pd.NA,
            },
            {
                "season_year": 2026,
                "sourcePlayerId": 102,
                "sourcePlayerName": "Second Player",
                "impactPercentile": 0.952127659574468,
                "draftYear": 2021,
            },
        ]
    )

    _write_records_json(source, path)
    loaded = _read_records_json(path)

    assert path.read_text(encoding="utf-8").lstrip().startswith("[")
    assert "José Example" in path.read_text(encoding="utf-8")
    assert loaded["sourcePlayerName"].tolist() == source["sourcePlayerName"].tolist()
    assert loaded["impactPercentile"].tolist() == pytest.approx(
        source["impactPercentile"].tolist()
    )
    assert pd.isna(loaded.loc[0, "draftYear"])
