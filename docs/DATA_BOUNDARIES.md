# Data boundaries

The project uses the same player-domain vocabulary for all data while preserving separate
provenance zones. Neutral entity names do not permit source identity to leak into roster output.

## Reference zone

Current path: `reference_data/`

Allowed contents:

- Source player IDs and names.
- Historical team identifiers and abbreviations.
- Raw, traditional, rate, and advanced statistics.
- Derived attributes associated with actual players.
- Source mappings, manifests, checksums, and license-status notes.

Rules:

- Keep raw and processed named data local and untracked.
- Do not load it from a game client or production runtime.
- Refresh intentionally and validate provenance and schema changes.
- Do not commit or redistribute upstream or derived named data without established rights.

## Roster-output zone

Current path: `generated_data/`

Planned version 2 path: `roster_data/`

Allowed contents:

- Independently generated player identities.
- Generated or adjusted statistics, ratings, and development values.
- Roster package metadata such as schema version, formula version, reference-package hash, and seed.

Forbidden contents:

- Source player IDs, source player names, source-row indexes, or source team IDs.
- A source-to-roster player crosswalk.
- Raw or transformed named reference records.

## Reports zone

Current path: `reports/`

Reports compare populations rather than identities. They may contain aggregated reference values,
but must not contain direct mappings between named reference players and roster players.

## Version 2 package boundary

The planned reference-data builder will publish a local, normalized reference package. The roster
generator may consume only that package and its versioned manifest; it must not read raw Parquet or
import source adapters. See the [version 2 plan](planning/README.md).
