# NBA GM Player Generator

This repository currently contains a Python prototype for transforming historical basketball data
into local reference profiles, deriving player ratings, and generating roster data for an NBA-style
GM simulation.

## Project status

The implemented version 1 pipeline remains runnable today. A version 2 redesign has been approved
and documented, but its new applications, contracts, commands, and frontend have not been
implemented.

- [Version 2 plan and delivery order](docs/planning/README.md)
- [Epics](docs/planning/README.md#delivery-order)
- [Decisions](docs/planning/DECISIONS.md)
- [Learnings](docs/planning/LEARNINGS.md)

Version 2 will organize the repository around two data subprojects:

1. A reference-data builder that accepts local Parquet from multiple sources and publishes a
   normalized CSV package.
2. A roster generator that consumes the reference package and publishes player-only CSVs separated
   into bio, traditional statistics, advanced statistics, and calculated attributes.

A supporting React workbench and Python API will show formula inputs and allow session-only previews
of weight, direction, and rating-anchor changes against top, searched, and pinned players.

## Current implementation

The current prototype includes:

- A Parquet adapter for a pinned `llimllib/nba_data` player-season snapshot.
- Named reference profiles for end-season years 2021 through 2026.
- Traditional, per-36, per-100, shooting, advanced, and physical inputs.
- Recency-weighted template sampling and deterministic roster generation.
- Explainable 25–99 player ratings, overall, impact percentile, and talent tier.
- Population comparison reports and automated Python tests.

The current package is intentionally a prototype. Ingestion, formulas, generation, comparison, and
CLI orchestration still live together under `src/player_generator/`. The planned version 2
boundaries in the planning documents should not be treated as current runtime interfaces.

## Quick start for version 1

Python 3.10 or newer is required.

```bash
python3 -m venv .venv
source .venv/bin/activate                 # Windows: .venv\Scripts\activate
python -m pip install -e '.[dev]'
python -m pytest
```

The tracked sample roster and comparison reports can be inspected without downloading source data.

To rebuild the local reference profiles and roster output:

```bash
player-generator download-reference
player-generator build-reference
player-generator generate
player-generator compare
```

Use `player-generator generate --seed 12345` to override the deterministic seed, or run all
available stages with `player-generator all --refresh-reference`.

These are current version 1 commands. They will be replaced as part of the clean version 2 break.

## Current layout

```text
config/default.yaml
reference_data/                  Local raw and processed named reference data
generated_data/                  Current roster output location
reports/                         Population comparison reports
schemas/                         Current combined roster JSON schema
src/player_generator/            Current Python package
tests/                           Current test suite
docs/planning/                    Approved version 2 design and user stories
```

See [Data boundaries](docs/DATA_BOUNDARIES.md) for provenance rules and
[Starter rating model](docs/RATING_MODEL.md) for the implemented formulas.

## Planned version 2 layout

The target is a monorepo with independently runnable applications and shared packages:

```text
apps/
  reference-data/
  roster-generator/
  formula-workbench/
packages/
  data-contracts/
  attribute-engine/
```

Reference data and roster generation are the two data subprojects. The formula workbench is a
supporting application over the shared contracts and calculation engine. See the
[version 2 planning index](docs/planning/README.md) rather than assuming these directories exist.

## Rating model

The current model derives inside scoring, three-point shooting, free-throw shooting, scoring volume,
playmaking, ball security, offensive and defensive rebounding, perimeter and interior defense,
stamina, durability, overall, impact percentile, and talent tier.

Metrics are converted to season-relative percentiles before weighted composition and interpolation
onto configured rating curves. Shooting percentages are stabilized toward the season average to
reduce small-sample effects. Defense remains a noisy estimate because the available measures contain
substantial team and context effects.

Version 2 will move the formulas into a declarative shared contract. The proposed schema and
baseline calculations are documented in
[Proposed player attribute formulas](docs/planning/ATTRIBUTE_FORMULAS.md).

## Data handling

Reference and roster data use the same player-domain vocabulary but remain different provenance
zones:

- Named source data, source IDs, and reconciliation mappings remain local reference data.
- Roster output must not contain source IDs, source names, or a source-to-roster crosswalk.
- Raw Parquet and derived named reference tables must not be committed or redistributed without
  established rights.
- Missing source fields are not invented simply to fill a planned schema.

The primary current input is `llimllib/nba_data`'s `data/playerstats.parquet`, pinned to commit
`a7bc98d73324300bd28d77260f45c98c239d1e87`. No root license file was observed in that upstream
repository when the snapshot was selected. ESPN ingestion is planned but not currently implemented.

Review [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and the
[source manifest](reference_data/source_manifest.json) before using third-party data.
