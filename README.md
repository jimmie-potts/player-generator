# NBA GM Player Generator

This monorepo contains independently runnable applications for building basketball reference data,
generating roster data, and developing an interactive formula workbench.

## Current architecture

```text
apps/
  reference-data/       Python reference-data CLI, configuration, source ingestion, and tests
  roster-generator/     Python roster CLI, configuration, generation, comparison, and tests
  formula-workbench/    React and TypeScript application shell
packages/
  data-contracts/       Shared versioned schemas, identifiers, and validation
  attribute-engine/     Shared percentile and player-rating calculations
```

Reference data and roster generation are the two data subprojects. The formula workbench is a
supporting application over the shared contracts and calculation engine.

The architecture boundary and normalized reference-package builder are implemented, but later
behavior remains planned:

- Reference data can register and normalize local NBA and ESPN Parquet inputs and atomically publish
  a validated version 1 CSV package. The pinned download and wide build remain legacy commands for
  the roster generator's current transitional input.
- Roster generation still produces a combined roster JSON and flat player CSV.
- Rating formulas retain their current Python definitions.
- The workbench currently renders a static application shell without data or formula behavior.

See the [version 2 planning index](docs/planning/README.md) for the remaining epics and story status.

## Setup

Python 3.10+, Node.js 22.12.0+, and npm are required.

```bash
python3 -m venv .venv
source .venv/bin/activate                 # Windows: .venv\Scripts\activate
python -m pip install -e '.[dev]'
npm install
```

Run the complete test suite:

```bash
make test
```

Or run each boundary independently:

```bash
python -m pytest
python -m ruff check .
npm run workbench:test
npm run workbench:build
```

Run the current data pipeline from a clean checkout with:

```bash
make all
```

This downloads or verifies the pinned reference source, builds the processed reference data,
generates the roster, and writes the comparison reports.

## Applications

### Reference data

```bash
reference-data --help
reference-data register --source-type nba_playerstats /path/to/playerstats.parquet
reference-data publish
reference-data publish --output /path/to/reference-v1
reference-data download
reference-data build
```

Registration validates and records local files without copying them into the repository. Source
types `nba_playerstats` and `espn_player_details` use adapter schema version 1, and their ignored
local provenance registry lives at `reference_data/registry/sources.json`. The current legacy
download remains pinned by `reference_data/source_manifest.json`. `publish` writes the version 1
relational CSVs, reconciliation audit, and deterministic manifest under
`reference_data/packages/reference-v1` by default. Registry and package output remain ignored.

### Roster generator

```bash
roster-generator --help
roster-generator generate
roster-generator compare
```

The generator reads `reference_data/processed/player_seasons_reference.csv`; it does not import or
invoke the reference-data application. Current outputs are:

```text
roster_data/default_roster.json
roster_data/players.csv
reports/comparison_report.json
reports/comparison_table.csv
```

The normalized player-only roster package is planned in EPIC-04.

### Formula workbench

```bash
npm run workbench:dev
npm run workbench:test
npm run workbench:build
```

The current React shell establishes the independently runnable frontend boundary. Formula
inspection, temporary editing, player search, and API integration remain part of EPIC-05 and
EPIC-06.

## Rating model

The implemented model derives inside scoring, three-point shooting, free-throw shooting, scoring
volume, playmaking, ball security, offensive and defensive rebounding, perimeter and interior
defense, stamina, durability, overall, impact percentile, and talent tier.

Metrics are converted to season-relative percentiles before weighted composition and interpolation
onto configured rating curves. Shooting percentages are stabilized toward the season average to
reduce small-sample effects. Defense remains an estimate because the available measures contain
substantial team and context effects.

Current calculations live in `packages/attribute-engine/`. The proposed declarative formula
contract is documented in
[Proposed player attribute formulas](docs/planning/ATTRIBUTE_FORMULAS.md).

## Architecture rules

- `reference_data_app` may use shared contracts and the attribute engine, but cannot import
  `roster_generator`.
- `roster_generator` consumes processed reference files and cannot import `reference_data_app`.
- `player_attribute_engine` is the authoritative Python calculation owner.
- The React workbench must call the future Python API rather than reimplement calculations.
- Source names, source IDs, and reconciliation mappings remain reference-only.

These rules are enforced by automated import-boundary and entrypoint tests.

## Data handling

- Raw Parquet and derived named reference tables must remain local and untracked.
- Roster output must not contain source IDs, source names, or a source-to-roster crosswalk.
- Missing source fields are not invented merely to fill a planned schema.
- The repository MIT license covers project software, not third-party data.

The primary current build input is `llimllib/nba_data`'s `data/playerstats.parquet`, pinned to commit
`a7bc98d73324300bd28d77260f45c98c239d1e87`. No root license file was observed in that upstream
repository when the snapshot was selected. ESPN player-detail files can be registered locally and
reconciled through the canonical model without exposing their source IDs to roster data.

Review [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md),
[Data boundaries](docs/DATA_BOUNDARIES.md), and the
[source manifest](reference_data/source_manifest.json) before using third-party data.
