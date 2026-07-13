from __future__ import annotations

import shutil
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from player_attribute_engine.ratings import rate_player_seasons
from player_data_contracts.io import read_json, sha256_file, write_json
from player_data_contracts.models import RATING_FIELDS

from reference_data_app.config import resolve_path
from reference_data_app.ingest import load_player_stats
from reference_data_app.snapshot import build_reference_snapshot

REFERENCE_SEASONS_FILE = "player_seasons_reference.csv"
REFERENCE_SNAPSHOT_FILE = "reference_players.csv"
REFERENCE_DISTRIBUTION_FILE = "reference_distribution.json"


def _raw_player_stats_from_manifest(config: dict[str, Any]) -> Path:
    manifest = read_json(resolve_path(config, "source_manifest"))
    raw_dir = resolve_path(config, "reference_raw_dir")
    sources = [source for source in manifest["sources"] if source["kind"] == "player_seasons"]
    if len(sources) != 1:
        raise ValueError("The source manifest must define exactly one player_seasons source.")
    return raw_dir / sources[0]["filename"]


def download_reference_data(config: dict[str, Any], force: bool = False) -> list[Path]:
    manifest = read_json(resolve_path(config, "source_manifest"))
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
            headers={"User-Agent": "nba-gm-reference-data/0.2"},
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
            "Run `reference-data download` first."
        )

    player_seasons = load_player_stats(
        player_stats_path,
        {int(year) for year in config["reference"]["seasons"]},
        config,
    )
    formula_population = player_seasons[player_seasons["positionGroup"] != "unknown"].copy()
    rated = rate_player_seasons(formula_population, config)
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
