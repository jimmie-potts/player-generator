# NBA GM Player Generator

An offline Python pipeline for using historical basketball data as a **local reference model** and
generating a completely fictional league for an NBA-style GM simulation.

The project deliberately separates two data domains:

```text
reference_data/                  generated_data/
Named, non-anonymized            Fictional, game-facing
Local calibration only           Safe runtime input
Source IDs and NBA names         No source IDs or NBA names
Ignored by Git by default        May be committed and shipped
```

Tracked fictional roster and report examples are available immediately. Named reference data is not
committed; download the pinned source snapshot before rebuilding ratings or generating a new roster.

## What is included

- A Parquet-based regular-season ingestion pipeline.
- Named, non-anonymized player-season profiles for end-season years 2021 through 2026
  (2020-21 through 2025-26).
- A six-season, recency-weighted template pool and a latest-season comparison snapshot.
- Direct per-game, per-36, per-100-possession and advanced-stat rating inputs.
- A deterministic generator for 30 fictional teams and 450 fictional players.
- Position, size, age, potential, archetype and development generation.
- Distribution and identity checks comparing fictional output with the named reference population.
- Pytest coverage and a GitHub Actions workflow.

## Quick start

Python 3.10 or newer is required.

```bash
python3 -m venv .venv
source .venv/bin/activate                 # Windows: .venv\Scripts\activate
python -m pip install -e '.[dev]'

# The tracked generated_data/ and reports/ examples are ready to inspect offline.
# Run the test suite without downloading reference data.
pytest
```

Generated files appear here:

```text
generated_data/default_roster.json
generated_data/fictional_players.csv
reports/comparison_report.json
reports/comparison_table.csv
```

## Rebuild the named reference data

The pinned `playerstats.parquet` snapshot is about 2.43 MB and is not committed. Download it before
building the local named reference tables or generating a new roster:

```bash
player-generator download-reference
player-generator build-reference
player-generator generate
player-generator compare
```

Use a different deterministic seed by replacing the `generate` command with
`player-generator generate --seed 12345`.

Or ensure the pinned input is present and rebuild all stages:

```bash
player-generator all --refresh-reference
```

The exact commit-pinned URL, expected SHA-256 hash and provenance notes are stored in
`reference_data/source_manifest.json`.

## Project layout

```text
.
├── config/default.yaml
├── generated_data/
│   ├── default_roster.json
│   └── fictional_players.csv
├── reference_data/
│   ├── raw/                              # downloaded inputs; Git-ignored
│   ├── processed/                        # named local outputs; Git-ignored
│   │   ├── player_seasons_reference.csv
│   │   ├── reference_players.csv
│   │   └── reference_distribution.json
│   └── source_manifest.json
├── reports/
│   ├── comparison_report.json
│   └── comparison_table.csv
├── schemas/default_roster.schema.json
├── docs/
├── scripts/
├── src/player_generator/
└── tests/
```

## Pipeline

```text
Pinned playerstats.parquet
          │
          ▼
Selected totals, per-36, per-100, advanced and bio fields
          │
          ▼
Broad position inference + stabilized shooting + 25-99 ratings
          │
          ├──────────────► latest-season comparison snapshot
          │
          ▼
Six-season weighted tier/position template sampling
          │
          ▼
Rating mutation + independent names/ages/physicals
          │
          ▼
30 balanced fictional teams
          │
          ├──────────────► generated_data/
          │                 game-facing roster
          ▼
Distribution, correlation and identity comparison
                            reports/
```

## Ratings

The model derives these ratings:

| Rating | Primary inputs |
|---|---|
| `insideScoring` | Stabilized 2P%, 2PA frequency, free-throw rate |
| `threePointShooting` | Stabilized 3P%, 3PA frequency |
| `freeThrowShooting` | Stabilized FT% |
| `scoringVolume` | Points per 100, usage, true shooting |
| `playmaking` | Assists per 36, assist percentage/ratio, assist/turnover, usage |
| `ballSecurity` | Inverse estimated turnover percentage and turnovers per 100, assist/turnover |
| `offensiveRebounding` | Offensive rebound percentage |
| `defensiveRebounding` | Defensive rebound percentage |
| `perimeterDefense` | Steals per 100, estimated defensive rating, DWS, DREB%, PIE |
| `interiorDefense` | Blocks per 100, DREB%, estimated defensive rating, DWS, PIE |
| `stamina` | Minutes per game and season minutes |
| `durability` | Games played relative to scheduled games |
| `overall` | PIE, estimated net rating, points per 100, minutes, TS% and availability |

Shooting percentages use empirical-Bayes-style stabilization: low-attempt players are pulled toward
the season league average. Ratings are percentile mapped separately within each season, which keeps
changes in league pace and shooting environment from overwhelming the scale.

The source does not provide position. Broad guard/wing/big groups are inferred from height and role
metrics for template stratification; they are not authoritative NBA positions. Defense also remains
noisy: ratings and defensive win shares include substantial team and context effects.

## Fictional generation

The generator does not write a source-player crosswalk. For each synthetic player it:

1. Chooses a talent tier and broad position from explicit league targets.
2. Samples a compatible named reference template from the six-season pool, weighted by both minutes
   and configured season recency.
3. Mutates every rating with configurable volatility.
4. Generates a non-colliding fictional name.
5. Generates age, height, weight, detailed position, archetype and development traits.
6. Assigns players to teams through a position-aware snake allocation.

The generated roster contains no `personId`, `sourcePlayerId`, `sourcePlayerName`, team abbreviation
or other direct reference identifier.

## Accuracy report

`reports/comparison_report.json` includes:

- Mean, standard deviation and quantiles for every rating.
- Quantile mean absolute error between reference and generated populations.
- Talent-tier and position-group shares.
- Mean absolute difference between rating-correlation matrices.
- Generated-name collisions against the reference names.
- Exact full-rating-vector matches.
- Nearest-reference rating distance.

This evaluates **population realism**, not whether a fictional player resembles a specific NBA
player.

## Configuration

Most tuning lives in `config/default.yaml`:

- End-season years, recency weights and minimum minutes.
- Shooting priors.
- Percentile-to-rating anchor curves.
- Per-attribute mutation volatility.
- Talent-tier counts and rating bounds.
- Position counts and per-team position targets.
- Physical distributions and generation seed.

A useful development loop is:

```text
change formulas/config
    → generate
    → inspect comparison report
    → simulate a season in the game
    → adjust
```

## Data handling

`reference_data/raw/` and files under `reference_data/processed/` are ignored by Git. Do not commit
or redistribute the downloaded Parquet file or derived named reference tables. The tracked fictional
examples under `generated_data/` contain no source identities and remain usable offline.

The game should load only `generated_data/default_roster.json`. Do not make the game runtime depend
on the named reference directory.

## Sources and notices

The primary input is `llimllib/nba_data`'s `data/playerstats.parquet`, pinned to commit
`a7bc98d73324300bd28d77260f45c98c239d1e87`. No root license file was observed in that upstream
repository when the snapshot was selected. `NocturneBear/NBA-Data-2010-2024` is retained only as a
manual validation source; it is not downloaded by the normal pipeline. The previous Brescou
dependency has been removed. ESPN analytics ingestion is deferred to a later phase.

See `THIRD_PARTY_NOTICES.md` and the source manifest before using any third-party data.
