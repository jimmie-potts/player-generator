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

- Keep raw, registered, normalized-package, and processed named data local and untracked.
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

The reference-data application publishes a validated version 1 normalized package and retains its
wide processed tables as a current legacy interface. The roster generator still consumes only that
legacy processed file without importing the reference pipeline or reading raw Parquet. US-008 will
move the consumer to the normalized package and versioned manifest. See the
[version 2 plan](planning/README.md).
