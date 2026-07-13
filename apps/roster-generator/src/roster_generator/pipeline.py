from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from player_data_contracts.io import write_json
from player_data_contracts.validation import validate_roster_payload

from roster_generator.comparison import compare_rosters
from roster_generator.config import resolve_path
from roster_generator.generator import generate_league

REFERENCE_SEASONS_FILE = "player_seasons_reference.csv"
REFERENCE_SNAPSHOT_FILE = "reference_players.csv"
ROSTER_FILE = "default_roster.json"
ROSTER_PLAYERS_FILE = "players.csv"
COMPARISON_REPORT_FILE = "comparison_report.json"
COMPARISON_TABLE_FILE = "comparison_table.csv"


def generate_roster(config: dict[str, Any], seed: int | None = None) -> tuple[Path, Path]:
    reference_dir = resolve_path(config, "reference_data_dir")
    seasons_path = reference_dir / REFERENCE_SEASONS_FILE
    if not seasons_path.exists():
        raise FileNotFoundError(
            f"Reference player seasons not found: {seasons_path}. "
            "Run `reference-data build` first."
        )
    reference = pd.read_csv(seasons_path, low_memory=False)
    league, players = generate_league(reference, config, seed=seed)
    validate_roster_payload(league)

    roster_dir = resolve_path(config, "roster_dir")
    roster_dir.mkdir(parents=True, exist_ok=True)
    roster_path = roster_dir / ROSTER_FILE
    players_path = roster_dir / ROSTER_PLAYERS_FILE
    write_json(roster_path, league)
    players.to_csv(players_path, index=False)
    return roster_path, players_path


def compare_roster(config: dict[str, Any]) -> tuple[Path, Path]:
    reference_path = resolve_path(config, "reference_data_dir") / REFERENCE_SNAPSHOT_FILE
    roster_players_path = resolve_path(config, "roster_dir") / ROSTER_PLAYERS_FILE
    if not reference_path.exists() or not roster_players_path.exists():
        raise FileNotFoundError(
            "Reference and roster player CSV files are required for comparison."
        )

    reference = pd.read_csv(reference_path, low_memory=False)
    roster = pd.read_csv(roster_players_path, low_memory=False)
    report, table = compare_rosters(reference, roster)

    reports_dir = resolve_path(config, "reports_dir")
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / COMPARISON_REPORT_FILE
    table_path = reports_dir / COMPARISON_TABLE_FILE
    write_json(report_path, report)
    table.to_csv(table_path, index=False)
    return report_path, table_path
