from __future__ import annotations

import json
import shutil
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from player_generator.comparison import compare_rosters
from player_generator.config import resolve_path
from player_generator.generator import generate_league
from player_generator.ingest import aggregate_player_seasons, load_bio_index, load_box_scores
from player_generator.ratings import build_reference_snapshot, rate_player_seasons
from player_generator.schema import RATING_FIELDS
from player_generator.util import read_json, sha256_file, write_json


REFERENCE_SEASONS_FILE = "player_seasons_reference.csv"
REFERENCE_SNAPSHOT_FILE = "reference_players_2023_24.csv"
REFERENCE_DISTRIBUTION_FILE = "reference_distribution.json"
GENERATED_ROSTER_FILE = "default_roster.json"
GENERATED_PLAYERS_FILE = "fictional_players.csv"
COMPARISON_REPORT_FILE = "comparison_report.json"
COMPARISON_TABLE_FILE = "comparison_table.csv"


def _raw_files_from_manifest(config: dict[str, Any]) -> tuple[list[Path], Path | None]:
    manifest = read_json(resolve_path(config, "source_manifest"))
    raw_dir = resolve_path(config, "reference_raw_dir")
    box_scores: list[Path] = []
    bio_path: Path | None = None
    for source in manifest["sources"]:
        target = raw_dir / source["filename"]
        if source["kind"] == "box_scores":
            box_scores.append(target)
        elif source["kind"] == "player_bios":
            bio_path = target
    return box_scores, bio_path


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
    box_score_paths, bio_path = _raw_files_from_manifest(config)
    missing = [path for path in box_score_paths if not path.exists()]
    if missing:
        names = ", ".join(path.name for path in missing)
        raise FileNotFoundError(
            f"Missing raw reference files: {names}. Run the download-reference command first."
        )

    games = load_box_scores(box_score_paths, set(config["reference"]["seasons"]))
    bios = load_bio_index(bio_path)
    player_seasons = aggregate_player_seasons(games, config, bios)
    minimum_minutes = float(config["reference"]["minimum_minutes"])
    eligible = player_seasons[
        (player_seasons["minutes"] >= minimum_minutes)
        & (player_seasons["positionGroup"] != "unknown")
    ].copy()
    rated = rate_player_seasons(eligible, config)
    snapshot = build_reference_snapshot(rated, config)

    processed_dir = resolve_path(config, "reference_processed_dir")
    processed_dir.mkdir(parents=True, exist_ok=True)
    seasons_path = processed_dir / REFERENCE_SEASONS_FILE
    snapshot_path = processed_dir / REFERENCE_SNAPSHOT_FILE
    rated.to_csv(seasons_path, index=False)
    snapshot.to_csv(snapshot_path, index=False)

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
    snapshot_path = processed_dir / REFERENCE_SNAPSHOT_FILE
    if not snapshot_path.exists():
        raise FileNotFoundError(
            f"Reference snapshot not found: {snapshot_path}. Build reference data first."
        )
    reference = pd.read_csv(snapshot_path, low_memory=False)
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
        raise FileNotFoundError("Reference and generated player CSV files are required for comparison.")

    reference = pd.read_csv(reference_path, low_memory=False)
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
    box_scores, _ = _raw_files_from_manifest(config)
    return bool(box_scores) and all(path.exists() for path in box_scores)


def reference_snapshot_exists(config: dict[str, Any]) -> bool:
    return (
        resolve_path(config, "reference_processed_dir") / REFERENCE_SNAPSHOT_FILE
    ).exists()
