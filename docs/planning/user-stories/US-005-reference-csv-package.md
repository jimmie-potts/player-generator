# US-005: Publish normalized reference CSVs

- **Status:** in_progress
- **Epic:** [EPIC-02](../epics/EPIC-02-reference-data.md)
- **Dependencies:** US-004

## User story

As a data consumer, I want normalized reference CSVs so that transformed data can be inspected and
consumed without Parquet or source-specific knowledge.

## Acceptance criteria

- Publish `players.csv`, `player_seasons.csv`, `player_stats.csv`,
  `player_advanced_stats.csv`, `player_source_ids.csv`, and `sources.csv`.
- Use the proposed interfaces in [DATA_CONTRACTS.md](../DATA_CONTRACTS.md), resolving the exact
  traditional and advanced metric lists before assigning contract version 1.
- `player_seasons.csv`, `player_stats.csv`, and `player_advanced_stats.csv` share the same aggregate
  `playerSeasonId` grain.
- Every header, key, type, required field, uniqueness rule, and relationship is governed by a
  versioned machine-readable contract.
- Missing optional values are empty; the builder does not fabricate unavailable fields.
- Write to a temporary package and publish atomically only after all validation passes.
- A package manifest records contract versions, input hashes, adapter versions, row counts, and a
  deterministic package content hash.
- Identical inputs and configuration produce identical CSV data and content hashes.

## Out of scope

- Committing or redistributing the resulting named data.
- Roster attributes or generated identities.

## Validation

- Golden packages cover expected headers and representative values.
- Relationship tests cover orphan keys, duplicates, type errors, missing required data, and partial
  publication cleanup.
- Determinism tests ignore only explicitly documented creation timestamps.

## Implementation notes

### 2026-07-13

- Started after US-004 completed in commit `d5148fc`; publication consumes only the validated
  canonical bundle and does not change the roster generator's US-008-owned legacy seam.
- Selected one machine-readable reference contract version governing all six relational CSVs, with
  exact ordered headers, scalar types, nullability, unique keys, and cross-table relationships.
- Selected sibling-directory staging with validation before a directory-level replacement. Failed
  writes or validation restore an existing package and remove temporary output.
- Finalized version 1 with 37 traditional and 19 advanced metric fields, each copied from the
  canonical adapter without ratings or later formula behavior. The packaged schema governs all six
  ordered CSV headers, scalar types, required/null rules, unique keys, player relationships, source
  types, and exact aggregate player-season key-set equality.
- Added `reference-data publish [--output PATH]`. Publication writes deterministic UTF-8/LF CSVs
  with empty optional cells, deterministic `audit.json`, and `manifest.json` containing input,
  contract, row-count, per-file hash, and package content-hash metadata.
- Synthetic golden, contract-failure, final-replace rollback, and end-to-end CLI fixtures passed.
  The full Python suite passed 88 tests and Ruff. Two builds from the ignored 6,908-row NBA input
  produced byte-identical CSV/audit files and content hash while differing only in `createdAt`.

## Completion notes

Pending. Record contract versions, final metric lists, package samples, commands, and validation
results before changing status to `complete`.
