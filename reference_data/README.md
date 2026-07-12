# Local non-anonymized reference data

This directory is deliberately separate from `generated_data/`.

It may contain real player names, source IDs, team abbreviations, historical box-score aggregates,
physical metadata and derived ratings. Its purpose is local calibration and regression testing—not
game loading.

## Layout

- `raw/`: downloaded source CSVs. Omitted from the starter archive because they are about 68 MB.
- `processed/player_seasons_reference.csv`: named player-season profiles for 2019-20 through
  2023-24.
- `processed/reference_players_2023_24.csv`: named comparison snapshot used by the generator.
- `processed/reference_distribution.json`: compact distribution summary.
- `source_manifest.json`: URLs, checksums, sizes, source repositories and license notes.

Both `raw/` and refreshed files in `processed/` are ignored by Git by default. The archive includes
a processed snapshot so generation and comparison work immediately after installing dependencies.

Rebuild the reference snapshot with:

```bash
player-generator download-reference
player-generator build-reference
```

Never load this directory from the game runtime. The game-facing default roster lives under
`generated_data/` and contains no source IDs or source-player names.
