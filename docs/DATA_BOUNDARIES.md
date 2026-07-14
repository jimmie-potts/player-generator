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
- Generated bio fields, adjusted statistics, and formula-derived attributes.
- Roster package metadata such as schema version, formula version, reference-package hash, and seed.

Forbidden contents:

- Source player IDs, source player names, source-row indexes, or source team IDs.
- A source-to-roster player crosswalk.
- Raw or transformed named reference records.

## Application boundary

The reference-data application publishes a validated version 2 normalized package with
season-relative attributes and retains its wide processed tables only as a standalone legacy
interface. The roster generator validates and consumes the normalized package and versioned
manifest without importing the reference application
or reading raw Parquet. It never publishes a template crosswalk. See the
[version 2 plan](planning/README.md).
