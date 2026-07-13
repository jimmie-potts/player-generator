# US-005: Publish normalized reference CSVs

- **Status:** ready
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

Append dated notes here while the story is active.

## Completion notes

Pending. Record contract versions, final metric lists, package samples, commands, and validation
results before changing status to `complete`.
