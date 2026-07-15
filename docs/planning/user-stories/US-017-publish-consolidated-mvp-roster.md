# US-017: Publish the consolidated MVP roster package

- **Status:** ready
- **Epic:** [EPIC-08](../epics/EPIC-08-nba-gm-mvp-handoff.md)
- **Dependencies:** US-016

## User story

As an NBA-GM developer, I want player-generator to publish the finalized MVP package so that the
simulation can validate and consume all currently generated player statistics.

## Acceptance criteria

- Publish exactly `players.csv`, consolidated `player_stats.csv`, `player_attributes.csv`, and
  `manifest.json` under the contract completed by US-016.
- Stop publishing roster `player_advanced_stats.csv`. Do not merge or rename the reference
  package's stat files; the roster generator may continue consuming separate normalized reference
  inputs internally.
- Preserve every current traditional, rate, possession, and advanced value in the consolidated row
  without changing its meaning, scale, derivation, bounds, or null policy.
- Preserve controlled mutation and every existing statistical consistency check after the output
  consolidation.
- Emit `season` as the statistical season-ending year and preserve the distinction from NBA-GM
  league context.
- Implement the manifest, deterministic package namespace, generator identity, and player-ID rules
  completed by US-016. Update exact-file validation, row counts, hashes, contract identifiers, and
  aggregate content hashing for the consolidated package.
- Preserve reference-identity leak protection, formula evaluation and provenance, deterministic
  bytes, validation-before-publication, and atomic replacement.
- Make the consolidated package the generator default. Do not dual-write the earlier roster format
  merely for compatibility with a consumer that has not integrated it.
- Make fixed-input generation match the US-016 conformance fixture and update current-state
  documentation only after the new publication path is implemented.

## Out of scope

- Changes to reference-data publication or its separate `player_seasons.csv`, `player_stats.csv`,
  and `player_advanced_stats.csv` tables.
- NBA-GM adapter implementation.
- ESPN-derived simulation statistics, deeper metrics, personality data, teams, assignments,
  contracts, and the review workbook.

## Validation

- Contract and semantic-statistics suites cover all consolidated fields and relationships.
- Golden-package and byte-determinism tests pass.
- Manifest tampering, exact-file-set, duplicate-key, and missing-row failures are covered.
- Identity-leak and atomic failure or rollback tests pass.
- Run the repository's enforced Python tests, Ruff checks, workbench tests, and workbench build.
- Synchronize `FILE_MANIFEST.sha256`, verify its hashes, and run `git diff --check`.

## Implementation notes

Append dated notes here while the story is active. Start only after US-016 has a reviewed schema and
fixture that NBA-GM can consume independently.

## Completion notes

Pending. Record the delivered contract and default path, golden hashes, pull request or commit,
validation results, deviations, follow-ups, decisions, and learnings before changing status to
`complete`.
