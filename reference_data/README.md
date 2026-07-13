# Local non-anonymized reference data

This directory is deliberately separate from the roster-output directory, `roster_data/`.

It may contain real player names, source IDs, team abbreviations, historical statistics, physical
metadata and derived ratings. Its purpose is local calibration and regression testing—not game
loading.

## Layout

- `raw/playerstats.parquet`: pinned 2.43 MB upstream snapshot; downloaded locally and Git-ignored.
- `registry/sources.json`: ignored local paths and provenance for registered Parquet inputs.
- `packages/reference-v1/`: ignored normalized version 1 CSV package, audit, and manifest.
- `processed/player_seasons_reference.csv`: named, rated player-season pool for end-season years
  2021 through 2026. This is the current legacy input sampled by the roster generator.
- `processed/reference_players.csv`: latest-season named comparison snapshot.
- `processed/reference_distribution.json`: compact distribution summary.
- `source_manifest.json`: pinned URL, checksum, size, provenance and license-status notes.

Upstream year values identify the season's ending year: 2021 means 2020-21 and 2026 means 2025-26.
The source has no position field, so the pipeline infers replaceable guard/wing/big buckets from
height and role metrics.

Raw, registered, normalized-package, and processed named data are ignored by Git. To build a version
1 reference package from caller-owned local inputs:

```bash
reference-data register --source-type nba_playerstats /path/to/playerstats.parquet
reference-data register --source-type espn_player_details /path/to/player-details.parquet
reference-data publish
```

The separate legacy path remains available until US-008 migrates roster generation:

```bash
reference-data download
reference-data build
```

Never load this directory from the game runtime. Current game-facing output lives under
`roster_data/` and contains no source IDs or source-player names. Do not commit or redistribute
the raw Parquet file or the derived named tables. The pinned `llimllib/nba_data` snapshot had no
observed root license file; see `THIRD_PARTY_NOTICES.md`.

[EPIC-02](../docs/planning/epics/EPIC-02-reference-data.md) implements local registration,
source-specific normalization, reconciliation, relational CSV contracts, and atomic publication.
The legacy downloader and wide processed tables remain only for the current roster seam; US-008
replaces that consumer without allowing it to read Parquet or import source adapters.
