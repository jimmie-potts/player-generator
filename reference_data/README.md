# Local non-anonymized reference data

This directory is deliberately separate from the roster-output directory, `roster_data/`.

It may contain real player names, source IDs, team abbreviations, historical statistics, physical
metadata and derived ratings. Its purpose is local calibration and regression testing—not game
loading.

## Layout

- `raw/playerstats.parquet`: pinned 2.43 MB upstream snapshot; downloaded locally and Git-ignored.
- `processed/player_seasons_reference.csv`: named, rated player-season pool for end-season years
  2021 through 2026. The generator samples this pool using configured recency weights.
- `processed/reference_players.csv`: latest-season named comparison snapshot.
- `processed/reference_distribution.json`: compact distribution summary.
- `source_manifest.json`: pinned URL, checksum, size, provenance and license-status notes.

Upstream year values identify the season's ending year: 2021 means 2020-21 and 2026 means 2025-26.
The source has no position field, so the pipeline infers replaceable guard/wing/big buckets from
height and role metrics.

Both `raw/` and files in `processed/` are ignored by Git. They are not included in a normal clone, so
rebuilding ratings or generating a new roster requires the download first:

```bash
reference-data download
reference-data build
```

Never load this directory from the game runtime. Current game-facing output lives under
`roster_data/` and contains no source IDs or source-player names. Do not commit or redistribute
the raw Parquet file or the derived named tables. The pinned `llimllib/nba_data` snapshot had no
observed root license file; see `THIRD_PARTY_NOTICES.md`.

The next reference-data stories will accept local Parquet files through source adapters and publish
normalized reference CSVs. The current downloader and wide processed tables remain authoritative until
[EPIC-02](../docs/planning/epics/EPIC-02-reference-data.md) is implemented.
