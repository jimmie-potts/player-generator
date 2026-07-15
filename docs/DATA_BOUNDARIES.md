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
interface. The roster generator and formula preview API validate and consume the normalized package
and versioned manifest without importing the reference application or reading raw Parquet. The
roster generator never publishes a template crosswalk.

The accepted player data contract version 1 integration baseline, which is not yet the publisher
default, treats reference and roster `players.csv`, `player_stats.csv`, and
`player_attributes.csv` as two profiles of one player-data interface. US-017 owns the publisher
cutover. The profiles' shared fields use the same ordered vocabulary, types, null representation,
units, bounds, meanings, and CSV formatting; a shared change must update both profiles together.
Parity does not require identical IDs, row values, grains, or complete package inventories.
Reference season context, source IDs, provenance, reconciliation, and audit data remain explicit
reference-only extensions. Roster generation inputs and metadata remain explicit roster-only
extensions. Neither kind of extension permits source identity or a source-to-roster crosswalk to
enter roster output.

The local-only preview API may return the configured season's reference display names and stable
internal player IDs for inspection. It does not expose source IDs or reconciliation mappings, write
reference or formula files, or provide a game-client or production data interface. See the
[implementation roadmap](planning/README.md) and
[preview API contract](../apps/formula-workbench/api/README.md).
