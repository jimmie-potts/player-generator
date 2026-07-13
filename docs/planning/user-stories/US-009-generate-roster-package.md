# US-009: Generate the normalized roster package

- **Status:** ready
- **Epic:** [EPIC-04](../epics/EPIC-04-roster-package.md)
- **Dependencies:** US-008

## User story

As a game developer, I want a normalized player-only CSV package so that bio, statistics, advanced
statistics, and attributes can be loaded independently.

## Acceptance criteria

- Publish `players.csv`, `player_stats.csv`, `player_advanced_stats.csv`,
  `player_attributes.csv`, and `manifest.json` as described in
  [DATA_CONTRACTS.md](../DATA_CONTRACTS.md).
- Generate player identities independently and use a stable roster `playerId` across every file.
- Produce traditional and advanced statistics by controlled mutation of a sampled reference
  player-season.
- Preserve valid relationships among minutes, totals, per-game, per-36, per-100, attempts, makes,
  percentages, and advanced fields after mutation.
- Omit fields lacking source inputs or approved generation rules.
- Exclude upstream names, player IDs, team IDs, source-row indexes, and any source-to-roster
  crosswalk.
- Write output atomically after all contract and relationship validation passes.
- The manifest records package version, reference-package hash, formula version, seed, configuration
  hash, row counts, and content hashes.
- Identical inputs produce identical data rows and hashes.

## Out of scope

- Team assignment, coach generation, contracts, health, personality, and unsupported tendencies.

## Validation

- Golden package and determinism tests.
- Statistical consistency properties and scale-bound checks.
- Identity-leak scans against reference IDs and names.
- Failure tests verify no partial package is published.

## Implementation notes

Append dated notes here while the story is active.

## Completion notes

Pending. Record final schemas, mutation rules, consistency tolerances, commands, and distribution
learnings before changing status to `complete`.
