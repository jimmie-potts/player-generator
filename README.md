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

The included starter snapshot lets you generate and compare rosters immediately. Raw game logs are
not bundled; a reproducible downloader can retrieve them when you want to rebuild the snapshot.

## What is included

- A historical regular-season ingestion pipeline.
- A named, non-anonymized 2019-20 through 2023-24 player-season reference table.
- A named 2023-24 comparison snapshot with derived 25-99 player ratings.
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

# Uses the included processed reference snapshot; no network call.
player-generator all

# Run tests.
pytest
```

Generated files appear here:

```text
generated_data/default_roster.json
generated_data/fictional_players.csv
reports/comparison_report.json
reports/comparison_table.csv
```

Use a different deterministic seed with:

```bash
player-generator generate --seed 12345
player-generator compare
```

## Rebuild the named reference data

The raw source files total roughly 68 MB and are omitted from the starter archive. To download and
rebuild the local named reference snapshot:

```bash
player-generator download-reference
player-generator build-reference
player-generator generate
player-generator compare
```

Or run everything and force a refreshed local reference snapshot:

```bash
player-generator all --refresh-reference
```

Exact source URLs, expected SHA-256 hashes and provenance notes are stored in
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
│   │   ├── reference_players_2023_24.csv
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
Historical named box scores
          │
          ▼
Named player-season totals and per-36 metrics
          │
          ▼
Stabilized shooting percentages and 25-99 ratings
          │
          ├──────────────► reference_data/processed/
          │                 local accuracy baseline
          ▼
Tier/position stratified template sampling
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

## Initial ratings

The starter model derives these ratings:

| Rating | Primary inputs |
|---|---|
| `insideScoring` | Stabilized 2P%, 2PA per 36, FTA per 36 |
| `threePointShooting` | Stabilized 3P%, 3PA per 36 |
| `freeThrowShooting` | Stabilized FT% |
| `scoringVolume` | Points per 36, minutes per game |
| `playmaking` | Assists per 36, assist/turnover ratio |
| `ballSecurity` | Inverse turnover-rate proxy, assist/turnover ratio |
| `offensiveRebounding` | Offensive rebounds per 36 |
| `defensiveRebounding` | Defensive rebounds per 36 |
| `perimeterDefense` | Steals, defensive rebounds and plus-minus proxies |
| `interiorDefense` | Blocks, defensive rebounds and plus-minus proxies |
| `stamina` | Minutes per game and season minutes |
| `durability` | Games played relative to scheduled games |
| `overall` | Game Score per 36, minutes, efficiency, plus-minus and availability |

Shooting percentages use empirical-Bayes-style stabilization: low-attempt players are pulled toward
the season league average. Ratings are percentile mapped separately within each season, which keeps
changes in league pace and shooting environment from overwhelming the scale.

Defense is the least reliable part of this starter model. Steals, blocks, rebounds and plus-minus do
not capture containment, rotations, screen navigation, matchup difficulty or deterrence. Treat the
defensive fields as simulation placeholders until a better data source is added.

## Fictional generation

The generator does not write a source-player crosswalk. For each synthetic player it:

1. Chooses a talent tier and broad position from explicit league targets.
2. Samples a compatible named reference template in memory.
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

- Historical seasons and minimum minutes.
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

`reference_data/raw/` and refreshed files under `reference_data/processed/` are ignored by Git. The
starter ZIP still contains a processed snapshot so it works out of the box. After extracting it into
a normal repository, accidental changes or expanded reference data will not be staged unless you
intentionally change `.gitignore`.

The game should load only `generated_data/default_roster.json`. Do not make the game runtime depend
on the named reference directory.

## Sources and notices

The source manifest currently points to:

- `NocturneBear/NBA-Data-2010-2024` for regular-season player box scores.
- `Brescou/NBA-dataset-stats-player-team` for optional physical and broad-position metadata.

Both repositories declare MIT licenses. See `THIRD_PARTY_NOTICES.md` and the source manifest before
redistributing any third-party data snapshot.
