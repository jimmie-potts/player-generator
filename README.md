# NBA GM Player Generator

This monorepo contains independently runnable applications for building basketball reference data,
generating roster data, and developing an interactive formula workbench.

## Current architecture

```text
apps/
  reference-data/       Python reference-data CLI, configuration, source ingestion, and tests
  roster-generator/     Python roster-package validation, generation, publication, and tests
  formula-workbench/    React formula-design client and Python preview API
packages/
  data-contracts/       Shared versioned schemas, identifiers, and validation
  attribute-engine/     Shared percentile and player-rating calculations
```

Reference data and roster generation are the two data subprojects. The formula workbench is a
supporting application over the shared contracts and calculation engine.

The batch-data foundation and local formula-design workflow are implemented:

- Reference data can register and normalize local NBA and ESPN Parquet inputs and atomically publish
  a validated version 2 CSV package with season-relative attributes. The pinned download and wide
  build remain standalone legacy commands.
- Roster generation validates that published package, selects deterministic templates, applies
  controlled statistical mutation, and atomically publishes a normalized player-only CSV package.
- Player attributes use the validated declarative formula document and shared Python evaluator.
- The formula preview API exposes version 1 formula, metric, player, and temporary recalculation
  endpoints over one integrity-checked season cohort.
- The React workbench consumes that API to inspect calculations, preview supported session-only
  formula adjustments, switch among tier, baseline Top 25, and custom player comparisons, and export
  the exact server-validated proposal document.

See the [version 2 planning index](docs/planning/README.md) for the remaining epics and story status.
For a presentation-oriented system walkthrough, see the
[current and projected technical architecture](docs/presentations/PLAYER_GENERATOR_TECHNICAL_OVERVIEW.md).

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

After registering caller-owned local reference inputs, run the normalized package pipeline with:

```bash
make all
```

This publishes the registered normalized reference package, then validates it and generates the
normalized roster package. It does not download, repair, or register reference inputs automatically.

## Applications

### Reference data

```bash
reference-data --help
reference-data register --source-type nba_playerstats /path/to/playerstats.parquet
reference-data publish
reference-data publish --output /path/to/reference-v2
reference-data publish --formula /path/to/formula.json
reference-data download
reference-data build
```

Registration validates and records local files without copying them into the repository. Source
types `nba_playerstats` and `espn_player_details` use adapter schema version 1, and their ignored
local provenance registry lives at `reference_data/registry/sources.json`. The current legacy
download remains pinned by `reference_data/source_manifest.json`. `publish` writes the version 2
relational CSVs, season-relative player attributes, reconciliation audit, and deterministic
manifest under `reference_data/packages/reference-v2` by default. Registry and package output
remain ignored.

### Roster generator

```bash
roster-generator --help
roster-generator generate
roster-generator generate --reference-package /path/to/reference-v2
roster-generator generate --output /path/to/roster-v1 --seed 42
```

The generator reads only a published reference package; it does not import or invoke the
reference-data application and never reads Parquet. Its default output is:

```text
roster_data/packages/roster-v1/
  players.csv
  player_stats.csv
  player_advanced_stats.csv
  player_attributes.csv
  manifest.json
```

Selection seasons, recency weights, games/minutes thresholds, roster size, replacement policy, and
seed are explicit YAML settings. Generated statistics share one possession basis and are validated
for totals, shooting arithmetic, percentages, per-game, per-36, per-100, and advanced-stat
relationships before atomic publication. Attributes are recalculated through the shared formula
engine. The manifest makes identical reference content, formula, semantic configuration, and seed
reproducible without exposing template identities.

### Formula workbench

Run the API and client in separate terminals:

```bash
# terminal 1
formula-preview-api --help
formula-preview-api --config apps/formula-workbench/api/config/default.yaml
# or: make formula-api

# terminal 2
npm run workbench:dev

# validation
npm run workbench:test
npm run workbench:build
```

The API loads the ignored local version 2 reference package by default, evaluates the complete
configured 2026 cohort through the shared engine, and serves bounded baseline, tier-representative,
search, detail, and request-local preview responses under `/api/v1`. It never writes formula
configuration, reference data, or presets. See the
[formula preview API contract](apps/formula-workbench/api/README.md) for endpoints, context hashes,
edit controls, limits, and error behavior.

The React client loads the active formula, metric metadata, and authoritative player explanations
from the API. Player Comparison defaults to three representatives from each populated talent tier
and offers mutually exclusive fixed baseline Top 25 and session-only custom-list views. The custom
list supports up to 25 searched players. Only the active view requests detailed player results, but
the API still calculates every rating, percentile, and rank against the complete fixed season
cohort. The client previews changes to existing component weights, directions, rating anchors, and
the proposed formula version. Superseded requests are cancelled, stale context is rejected, and the
browser never calculates ratings itself.

Edits and the custom list disappear on reload. Export downloads the API's exact validated full
formula JSON, which can be passed to `roster-generator generate --formula`; it does not activate or
persist the proposal. Authentication, named sessions, arbitrary browser expressions, deployment,
and production hosting remain out of scope.

## Rating model

The implemented model derives inside scoring, three-point shooting, free-throw shooting, scoring
volume, playmaking, ball security, offensive and defensive rebounding, perimeter and interior
defense, stamina, durability, overall, impact percentile, and talent tier.

Metrics are converted to season-relative percentiles before weighted composition and interpolation
onto formula-declared rating curves. Shooting percentages are stabilized toward the season average
with versioned priors. Nulls, eligibility, ties, inverse direction, anchors, schedules, output scale,
and talent tiers are all explicit in formula version `1.0.0`. Defense remains an estimate because
the available measures contain substantial team and context effects.

The active document and calculations live in `packages/attribute-engine/`; the structural formula
schema lives in `packages/data-contracts/`. See the [current rating model](docs/RATING_MODEL.md) and
[player attribute formulas](docs/planning/ATTRIBUTE_FORMULAS.md).

## Architecture rules

- `reference_data_app` may use shared contracts and the attribute engine, but cannot import
  `roster_generator`.
- `roster_generator` consumes published reference packages and cannot import `reference_data_app`.
- `player_attribute_engine` is the authoritative Python calculation owner.
- `formula_preview_api` reads only a validated published reference package and calls the shared
  attribute engine; it does not import either data application or write package/formula state.
- The React workbench calls the Python API rather than reimplementing calculations; its edits and
  custom list are session-only, and exports use the exact server-validated preview document.
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

Review the [data boundaries](docs/DATA_BOUNDARIES.md) and the
[source manifest](reference_data/source_manifest.json) before using third-party data.
