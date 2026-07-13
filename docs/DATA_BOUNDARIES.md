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

Path: `roster_data/`

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

## Application boundary

The reference-data application currently publishes local processed tables. The roster generator
consumes those files without importing the reference pipeline or reading raw Parquet. US-005 and
US-008 will replace this transitional seam with a normalized package and versioned manifest. See the
[version 2 plan](planning/README.md).
