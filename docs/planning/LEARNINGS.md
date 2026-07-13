# Version 2 learning log

This is an append-oriented record of reusable facts discovered while planning or implementing the
redesign. Each completed story must add any relevant findings here and retain detailed evidence in
its completion notes.

## Planning baseline — 2026-07-12

- The current implementation is a single Python package in which ingestion, formulas, roster
  generation, comparison, and CLI orchestration directly import one another.
- Current rating formulas are Python dictionaries in `ratings.py`; weights and inputs cannot be
  edited safely by a browser without first extracting a declarative contract.
- The current source manifest downloads one pinned `playerstats.parquet` URL. Version 2 local-file
  ingestion is a behavior change, not just a new command name.
- The current processed model uses wide player-season and latest-season CSVs. Moving to normalized
  contracts requires explicit keys, join validation, and provenance tables.
- The current generator emits a combined roster JSON and a flattened player CSV. Version 2 instead
  publishes a player-only package split by concern.
- Current team definitions and assignments exist, but first-release version 2 team output is
  deliberately out of scope.
- The upstream `llimllib/nba_data` snapshot has no observed root license. Raw and transformed named
  reference data should remain local and untracked unless redistribution rights are established.
- ESPN play-style data can improve future attributes, but source-ID reconciliation and schema
  differences make it a separate adapter and formula-extension story.

### 2026-07-12 — US-001

- Setuptools can discover packages across multiple app and package source roots while exposing one
  root editable install and separate console entrypoints.
- Physical directories alone do not enforce application separation; AST import tests make the
  reference-to-roster prohibition executable.
- The current processed player-season CSV is only a transitional application seam. It is not the
  versioned normalized reference package planned by US-005 and US-008.
- A static React shell is sufficient to prove the frontend build, test, and runtime boundary without
  pulling formula or API behavior forward from later epics.
- Root aggregate commands must include source acquisition or verification so they work from a clean
  checkout, even when lower-level build commands intentionally fail fast on missing inputs.
- Declared runtime engine ranges should match the strictest locked build-tool requirement; Vite 7
  requires Node.js 22.12 or newer within the Node 22 line.

### 2026-07-12 — US-002

- Output terminology appears in paths, code identifiers, report JSON keys, CSV headers, schemas,
  fixtures, and documentation; all of those surfaces must move together.
- Generated examples and reports should be rebuilt from their owning applications after interface
  renames rather than edited by hand.

### 2026-07-13 — US-003

- Parquet metadata does not identify the application adapter schema version; local registration
  must pair each file with an explicit source type and adapter version.
- Idempotent registration must preserve its first processing timestamp as well as its content hash,
  otherwise unchanged inputs would make later package provenance non-deterministic.
- Registration can remain safe for named third-party data by storing only an ignored local path and
  provenance record; the application never needs to copy source bytes into its workspace.
- A conservative adapter may require only observed stable fields and leave other source-specific
  values unavailable rather than treating a guessed upstream schema as a supported contract.

### 2026-07-13 — US-004

- Source IDs must remain namespaced by source type; equal-looking values from different providers
  are not identity evidence. Reviewed overrides and unique normalized exact names are separate,
  auditable reconciliation rules.
- `team_count` is unavailable in older NBA rows. Canonical team identity is safe only when that
  field explicitly equals one; last-team and aggregate source labels remain audit context.
- Repeated seasons can disagree on bio values such as height or weight. Declared source precedence
  still needs a deterministic within-source rule, and latest season followed by source ID provides
  one while preserving every distinct candidate in the conflict audit.
- Adapters should map only fields whose units and meaning are explicit. Ignoring ambiguous ESPN
  height and weight columns avoids silently converting an unknown upstream contract.
- Parquet logical date and timestamp columns can surface as Python dates or pandas timestamps.
  Date-valued adapter fields need field-specific normalization to `YYYY-MM-DD` instead of generic
  scalar serialization that retains a time component.
- Optional numeric source fields can encode missing values as blank text. Treat blanks as null only
  where the adapter already permits numeric text, and keep required-field wrappers responsible for
  rejecting the resulting missing player IDs or seasons.
- Opaque player IDs anchored to a primary namespaced identity remain stable when a supplemental
  source is later reconciled, while opaque player-season IDs make aggregate grain executable.

### 2026-07-13 — US-005

- A machine-readable CSV contract must govern ordered headers as well as field types and keys;
  validating row mappings alone cannot detect a consumer-visible header reorder.
- Validate the serialized staging directory before publication. This catches encoding, empty-cell,
  numeric-format, and header errors that in-memory canonical validation cannot observe.
- A deterministic package content hash can cover contract CSVs and audit while excluding the
  manifest's `createdAt`; persisted registration timestamps keep provenance stable between builds.
- Directory-level publication needs a same-parent staging directory and backup restoration so a
  failed final rename cannot leave a partial package or destroy the last valid one.
- Real source files may encode unavailable optional text as whitespace. Normalize it to null before
  CSV writing so the contract produces an empty cell rather than invalid non-empty text.

## Entry format

Add new entries under a dated heading and identify the story that produced the learning:

```text
### YYYY-MM-DD — US-NNN

- What was learned.
- Why it matters to later stories.
- Any constraint or validation that should be reused.
```
