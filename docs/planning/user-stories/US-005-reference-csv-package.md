# US-005: Publish normalized reference CSVs

- **Status:** complete
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
- PR review made input provenance fail closed: publication verifies every registered source's hash
  and row count before normalization and repeats verification after reading. Drift therefore stops
  before staging or replacing a package, while the existing destination remains intact.
- Review follow-up validation passed 20 focused registration/publication tests and all 98 Python
  tests, plus Ruff, workbench tests, and the production workbench build.

## Completion notes

- **Completed:** 2026-07-13
- **Branch and implementation commit:** `agent/implement-us-003-us-005`; `07c63ef`.
- **Delivered:** `reference-data publish`; the packaged `reference-v1.schema.json` contract and
  reusable table/package validators; six contract-ordered UTF-8/LF CSVs; deterministic
  reconciliation audit; manifest version 1; and staged, validated, backup-restored directory
  replacement with failure cleanup.
- **Contract version and metrics:** Reference contract version 1 uses the exact headers in
  [DATA_CONTRACTS.md](../DATA_CONTRACTS.md): 37 traditional and 19 advanced metrics after the three
  aggregate player-season identity columns. Missing optional values are empty, and starts, birth
  data, or other unavailable inputs are not invented.
- **Manifest and determinism:** The manifest records version 1 for every CSV, registered input
  hashes and adapter versions, row counts, file hashes, and a content hash over all six CSVs plus
  `audit.json`. `createdAt` is the only per-publication timestamp and is excluded from that hash;
  stable registration timestamps remain part of `sources.csv`.
- **Local package sample:** The ignored pinned NBA file produced 1,693 player rows, 1,693 source-ID
  rows, one provenance row, and 6,908 rows in each season-grain table. Two publications produced
  byte-identical CSVs and audit plus content hash
  `8cffd80a96a8fe5d2e0a937eadf788601e1c185d1175baeb8858b5ba285264a5` while their `createdAt`
  values differed.
- **Compatibility boundary:** The legacy pinned `download` and wide `build` remain only because the
  current roster generator consumes that interface. US-008 owns its move to this package; no roster
  runtime, formula, rating, or generated identity behavior changed here.
- **Validation:** `.venv/bin/python -m pytest -q` passed 88 tests; `.venv/bin/python -m ruff check .`,
  `git diff --check`, `npm run workbench:test`, and `npm run workbench:build` passed. Golden headers,
  optional empties, type errors, missing required values, duplicates, orphans, mismatched season key
  sets, deterministic hashes, validation cleanup, final-replace rollback, and CLI publication are
  covered.
- **Follow-up:** US-006 consumes the reference metric vocabulary for declarative formulas. US-008
  validates and consumes a published package without accessing this application's registry or
  adapters.
- **Learning:** Validation must run against the serialized staging directory, not only in-memory
  rows; the real input also showed that whitespace-only optional source text must normalize to null
  before contract serialization.
