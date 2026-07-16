# US-017: Publish player data contract version 1

- **Status:** in_progress
- **Epic:** [EPIC-08](../epics/EPIC-08-nba-gm-mvp-handoff.md)
- **Dependencies:** US-016

## User story

As a player-generator maintainer, I want the reference and roster publishers to emit the finalized
version 1 profiles so NBA-GM can consume the roster profile while both producer profiles continue
to evolve together.

## Acceptance criteria

- Publish the exact roster profile of `players.csv`, consolidated `player_stats.csv`,
  `player_attributes.csv`, and `manifest.json` under the contract completed by US-016.
- Publish the reference profile's corresponding `players.csv`, consolidated `player_stats.csv`, and
  `player_attributes.csv` from the same shared definitions. Retain declared reference-only
  `player_source_ids.csv`, `sources.csv`, `audit.json`, and manifest content. Publish reference
  season context directly in `player_stats.csv`.
- Enforce each version 1 profile's exact canonical inventory and reject undeclared extra files. The
  roster generator must consume the validated reference profile through its public contract and
  must not recreate a private alternate field definition.
- Apply the exact shared header, field semantics, types, base null policy, units, bounds,
  classifications, formatting, and deterministic ordering completed by US-016 to both outputs.
  Implement only the declared profile-specific keys and availability-based null overrides.
- Publish every governed reference or roster traditional, rate, and advanced metric and its semantic
  meaning in the applicable consolidated row, plus the roster profile's explicit `possessions`
  extension. Apply the reviewed representation, requiredness, nullability, and bounds from US-016;
  do not silently drop a metric or introduce a conflicting definition.
- Preserve controlled mutation and every governed statistical consistency check.
- Emit `season` as the statistical season-ending year and preserve the distinction from NBA-GM
  league context.
- Preserve the existing deterministic `player_[0-9a-f]{16}` IDs as package-scoped keys and implement
  the manifest and generator identity rules completed by US-016. Keep aggregate content identity
  separate so consumers can pair it with `playerId` for source traceability without rewriting player
  keys. Update exact-file validation, row counts, hashes, and contract identifiers for the
  consolidated package.
- Implement the common manifest envelope and declared profile extensions from US-016 in both
  publishers. Update the roster generator and preview API reference-package readers, contract
  validators, packaged schemas, fixtures, and documentation in the same change so no supported
  path observes mixed profile definitions.
- Preserve reference-identity leak protection, formula evaluation and provenance, deterministic
  bytes, validation-before-publication, and atomic replacement.
- Make the version 1 profiles the reference publisher and roster generator defaults and publish only
  their canonical inventories.
- Make fixed-input reference publication and roster generation match their US-016 conformance
  fixtures and update current-state documentation only after both version 1 publication paths are
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

- **2026-07-15:** Started after PR review fixed the version 1 inventory: five reference-profile CSVs
  plus audit and manifest, and three roster-profile CSVs plus manifest. Both publishers, supported
  readers, validators, fixtures, defaults, and current-state documentation are being aligned to that
  one format. Final validation and completion evidence remain pending.

## Completion notes

Pending. Record the delivered contracts and default paths, declared profile extensions, golden
hashes, pull request or commit, validation results, deviations, follow-ups, decisions, and learnings
before changing status to `complete`.
