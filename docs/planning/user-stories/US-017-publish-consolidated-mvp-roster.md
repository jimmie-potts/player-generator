# US-017: Publish parity-aligned MVP player packages

- **Status:** ready
- **Epic:** [EPIC-08](../epics/EPIC-08-nba-gm-mvp-handoff.md)
- **Dependencies:** US-016

## User story

As a player-generator maintainer, I want the reference and roster publishers to emit the finalized
parity-aligned player files so NBA-GM can consume the roster profile while both producer profiles
continue to evolve together.

## Acceptance criteria

- Publish the exact roster profile of `players.csv`, consolidated `player_stats.csv`,
  `player_attributes.csv`, and `manifest.json` under the contract completed by US-016.
- Publish the reference profile's corresponding `players.csv`, consolidated `player_stats.csv`, and
  `player_attributes.csv` from the same shared definitions. Retain declared reference-only
  `player_seasons.csv`, `player_source_ids.csv`, `sources.csv`, `audit.json`, and manifest content.
- Stop publishing `player_advanced_stats.csv` from both profiles. The roster generator must consume
  the parity-aligned validated reference package through its public contract and must not recreate a
  private alternate field definition.
- Apply the exact shared header, field semantics, types, base null policy, units, bounds,
  classifications, formatting, and deterministic ordering completed by US-016 to both outputs.
  Implement only the declared profile-specific keys and availability-based null overrides.
- Preserve every currently published reference or roster traditional, rate, possession, and
  advanced metric and its semantic meaning in the applicable consolidated row. Apply the reviewed
  representation, requiredness, nullability, and bounds harmonization from US-016; do not silently
  drop a metric or retain a conflicting legacy definition.
- Preserve controlled mutation and every existing statistical consistency check after the output
  consolidation.
- Emit `season` as the statistical season-ending year and preserve the distinction from NBA-GM
  league context.
- Implement the manifest, deterministic package namespace, generator identity, and player-ID rules
  completed by US-016. Update exact-file validation, row counts, hashes, contract identifiers, and
  aggregate content hashing for the consolidated package.
- Implement the common manifest envelope and declared profile extensions from US-016 in both
  publishers. Update the roster generator and preview API reference-package readers, contract
  validators, packaged schemas, fixtures, and documentation in the same change so no supported
  path observes a half-migrated contract.
- Preserve reference-identity leak protection, formula evaluation and provenance, deterministic
  bytes, validation-before-publication, and atomic replacement.
- Make the consolidated profiles the reference publisher and roster generator defaults. Do not
  dual-write the earlier stat split merely for compatibility with a consumer that has not integrated
  it.
- Make fixed-input reference publication and roster generation match their US-016 conformance
  fixtures and update current-state documentation only after both new publication paths are
  implemented.

## Out of scope

- NBA-GM adapter implementation.
- ESPN-derived simulation statistics, deeper metrics, personality data, teams, assignments,
  contracts, and the review workbook.

## Validation

- Contract and semantic-statistics suites cover all consolidated fields and relationships.
- Cross-profile tests prove all shared fields and formatting remain in parity and reject undeclared
  profile differences, including a regression for a one-sided field, ordering, or type change.
- Golden-package and byte-determinism tests pass.
- Manifest tampering, each profile's exact-file set and common envelope, duplicate-key, and
  missing-row failures are covered.
- Identity-leak and atomic failure or rollback tests pass.
- Run the repository's enforced Python tests, Ruff checks, workbench tests, and workbench build.
- Synchronize `FILE_MANIFEST.sha256`, verify its hashes, and run `git diff --check`.

## Implementation notes

Append dated notes here while the story is active. Start only after US-016 has a reviewed schema and
fixture that NBA-GM can consume independently.

## Completion notes

Pending. Record the delivered contracts and default paths, declared profile extensions, golden
hashes, pull request or commit, validation results, deviations, follow-ups, decisions, and learnings
before changing status to `complete`.
