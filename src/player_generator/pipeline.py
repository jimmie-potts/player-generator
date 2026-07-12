from __future__ import annotations

import shutil
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from player_generator.comparison import compare_rosters
from player_generator.config import resolve_path
from player_generator.generator import generate_league
from player_generator.ingest import load_player_stats
from player_generator.ratings import build_reference_snapshot, rate_player_seasons
from player_generator.schema import RATING_FIELDS
from player_generator.util import read_json, sha256_file, write_json

REFERENCE_SEASONS_FILE = "player_seasons_reference.json"
REFERENCE_SNAPSHOT_FILE = "reference_players.json"
REFERENCE_DISTRIBUTION_FILE = "reference_distribution.json"
GENERATED_ROSTER_FILE = "default_roster.json"
GENERATED_PLAYERS_FILE = "fictional_players.csv"
COMPARISON_REPORT_FILE = "comparison_report.json"
COMPARISON_TABLE_FILE = "comparison_table.csv"


def _write_records_json(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_json(
        path,
        orient="records",
        indent=2,
        force_ascii=False,
        double_precision=15,
    )


def _read_records_json(path: Path) -> pd.DataFrame:
    return pd.read_json(path, orient="records", convert_dates=False)


def _raw_player_stats_from_manifest(config: dict[str, Any]) -> Path:
    manifest = read_json(resolve_path(config, "source_manifest"))
    raw_dir = resolve_path(config, "reference_raw_dir")
    sources = [source for source in manifest["sources"] if source["kind"] == "player_seasons"]
    if len(sources) != 1:
        raise ValueError("The source manifest must define exactly one player_seasons source.")
    return raw_dir / sources[0]["filename"]


def download_reference_data(config: dict[str, Any], force: bool = False) -> list[Path]:
    manifest_path = resolve_path(config, "source_manifest")
    manifest = read_json(manifest_path)
    raw_dir = resolve_path(config, "reference_raw_dir")
    raw_dir.mkdir(parents=True, exist_ok=True)
    downloaded: list[Path] = []

    for source in manifest["sources"]:
        target = raw_dir / source["filename"]
        expected_hash = source.get("sha256")
        if target.exists() and not force:
            if not expected_hash or sha256_file(target) == expected_hash:
                downloaded.append(target)
                continue

        temporary = target.with_suffix(target.suffix + ".part")
        request = urllib.request.Request(
            source["url"],
            headers={"User-Agent": "nba-gm-player-generator/0.1"},
        )
        with urllib.request.urlopen(request, timeout=120) as response, temporary.open("wb") as out:
            shutil.copyfileobj(response, out)
        temporary.replace(target)

        actual_hash = sha256_file(target)
        if expected_hash and actual_hash != expected_hash:
            target.unlink(missing_ok=True)
            raise ValueError(
                f"Checksum mismatch for {source['filename']}: {actual_hash} != {expected_hash}"
            )
        downloaded.append(target)
    return downloaded


def build_reference_data(config: dict[str, Any]) -> tuple[Path, Path]:
    player_stats_path = _raw_player_stats_from_manifest(config)
    if not player_stats_path.exists():
        raise FileNotFoundError(
            f"Missing raw reference file: {player_stats_path.name}. "
            "Run the download-reference command first."
        )

    player_seasons = load_player_stats(
        player_stats_path,
        {int(year) for year in config["reference"]["seasons"]},
        config,
    )
    minimum_games = int(config["reference"].get("minimum_games", 0))
    minimum_minutes = float(config["reference"]["minimum_minutes"])
    eligible = player_seasons[
        (player_seasons["games"] >= minimum_games)
        & (player_seasons["minutes"] >= minimum_minutes)
        & (player_seasons["positionGroup"] != "unknown")
    ].copy()
    rated = rate_player_seasons(eligible, config)
    snapshot = build_reference_snapshot(rated, config)

    processed_dir = resolve_path(config, "reference_processed_dir")
    processed_dir.mkdir(parents=True, exist_ok=True)
    seasons_path = processed_dir / REFERENCE_SEASONS_FILE
    snapshot_path = processed_dir / REFERENCE_SNAPSHOT_FILE
    _write_records_json(rated, seasons_path)
    _write_records_json(snapshot, snapshot_path)

    rating_fields = [*RATING_FIELDS, "overall"]
    distribution = {
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "comparisonSeason": config["reference"]["comparison_season"],
        "playerSeasonRows": int(len(rated)),
        "comparisonPlayers": int(len(snapshot)),
        "ratings": {
            field: {
                "mean": round(float(snapshot[field].mean()), 3),
                "std": round(float(snapshot[field].std(ddof=0)), 3),
                "p10": round(float(snapshot[field].quantile(0.10)), 3),
                "p50": round(float(snapshot[field].quantile(0.50)), 3),
                "p90": round(float(snapshot[field].quantile(0.90)), 3),
            }
            for field in rating_fields
        },
        "positionGroups": snapshot["positionGroup"].value_counts().to_dict(),
        "talentTiers": snapshot["talentTier"].value_counts().to_dict(),
    }
    write_json(processed_dir / REFERENCE_DISTRIBUTION_FILE, distribution)
    return seasons_path, snapshot_path


def generate_roster(config: dict[str, Any], seed: int | None = None) -> tuple[Path, Path]:
    processed_dir = resolve_path(config, "reference_processed_dir")
    seasons_path = processed_dir / REFERENCE_SEASONS_FILE
    if not seasons_path.exists():
        raise FileNotFoundError(
            f"Reference player seasons not found: {seasons_path}. Build reference data first."
        )
    reference = _read_records_json(seasons_path)
    league, players = generate_league(reference, config, seed=seed)

    generated_dir = resolve_path(config, "generated_dir")
    generated_dir.mkdir(parents=True, exist_ok=True)
    roster_path = generated_dir / GENERATED_ROSTER_FILE
    players_path = generated_dir / GENERATED_PLAYERS_FILE
    write_json(roster_path, league)
    players.to_csv(players_path, index=False)
    return roster_path, players_path


def compare_generated_roster(config: dict[str, Any]) -> tuple[Path, Path]:
    reference_path = resolve_path(config, "reference_processed_dir") / REFERENCE_SNAPSHOT_FILE
    generated_path = resolve_path(config, "generated_dir") / GENERATED_PLAYERS_FILE
    if not reference_path.exists() or not generated_path.exists():
        raise FileNotFoundError(
            "Reference player JSON and generated player CSV are required for comparison."
        )

    reference = _read_records_json(reference_path)
    generated = pd.read_csv(generated_path, low_memory=False)
    report, table = compare_rosters(reference, generated)

    reports_dir = resolve_path(config, "reports_dir")
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / COMPARISON_REPORT_FILE
    table_path = reports_dir / COMPARISON_TABLE_FILE
    write_json(report_path, report)
    table.to_csv(table_path, index=False)
    return report_path, table_path


def raw_reference_files_exist(config: dict[str, Any]) -> bool:
    return _raw_player_stats_from_manifest(config).exists()


def reference_snapshot_exists(config: dict[str, Any]) -> bool:
    return (
        resolve_path(config, "reference_processed_dir") / REFERENCE_SNAPSHOT_FILE
    ).exists()
