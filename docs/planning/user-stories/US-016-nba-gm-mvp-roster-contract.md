# US-016: Freeze player data contract version 1

- **Status:** in_progress
- **Epic:** [EPIC-08](../epics/EPIC-08-nba-gm-mvp-handoff.md)
- **Dependencies:** US-009, US-015, and versioned contract conventions from US-005

## User story

As a player-data integrator, I want the baseline version 1 reference and roster profiles to derive
from shared definitions, with a finalized roster fixture for NBA-GM, so producer and consumer work
can proceed independently without the two player-generator profiles drifting.

## Acceptance criteria

- Freeze one machine-readable contract family at version 1 with reference and roster profiles for
  corresponding `players.csv`, `player_stats.csv`, and `player_attributes.csv` files. Derive every
  shared field definition from one source rather than copying it between profile schemas.
- Freeze the roster profile whose exact package contains `players.csv`, `player_stats.csv`,
  `player_attributes.csv`, and `manifest.json`.
- Define both profiles' `player_stats.csv` as one ordered row containing the governed traditional,
  rate (including per-100), and advanced fields after their profile-specific key prefix. Declare
  roster-only explicit `possessions` as a profile extension; reference publishes per-100 rates but
  no possession total.
- Define the exact shared ordered columns, types, base null policy, meanings, units or scales,
  bounds, primitive or derived classifications, season convention, CSV encoding, line endings,
  null encoding, numeric serialization, and deterministic ordering. A shared addition, removal,
  rename, or formatting change must apply to both profiles in the same contract change.
- Declare every profile-only key, column, file, manifest field, and required-or-null override with
  its rationale. Keep reference season context, source IDs, provenance, reconciliation, and audit
  data reference-only; keep roster generation inputs and metadata roster-only. A profile extension
  must not redefine a shared field's type, meaning, unit, bounds, or derivation.
- Require exactly one statistics row per roster player and one statistical-basis season per player.
  Preserve `playerId` as the unique cross-file key and require exact player-key equality across all
  three CSVs.
- Define `season` as the sampled statistical season's four-digit ending year: `2025` means the
  2024-25 season. State that it is not NBA-GM's fictional league season and may differ between
  generated players in one package.
- Keep `player_attributes.csv` at player grain. Its values rate the player's sole statistics row,
  and each row retains `formulaVersion`.
- Document every statistics field's ordered position, scalar type, nullability, bounds, unit or
  scale, and classification as a primitive value or a derived total, rate, percentage, frequency,
  or advanced metric.
- Preserve the possession basis and statistical identities in D-018, D-019, and D-021.
- Define the manifest's exact file inventory, contract identifiers, generator and ID-scheme
  identity, row counts, hashes, formula metadata, reference-package hash, seed, configuration hash,
  and aggregate content hash. Define a deterministic package namespace or equivalent ID input so
  materially different same-seed packages do not silently reuse player IDs.
- Resolve and document the `age` and effective-date interpretation at the handoff. NBA-GM-owned
  fields such as `birthDate`, position, league assignment, contracts, and simulation-specific
  ratings must have an explicit owner and must not be silently fabricated by this contract.
- Resolve the shared statistics payload so both profiles represent shared counts, `games`,
  `minutes`, percentages, and rates consistently. Keep the roster's explicit `possessions` total as
  a declared extension and reference season context in `player_stats.csv` so each governed value
  has one authoritative representation.
- Define a common manifest envelope for contract family, version, profile, file row counts and
  hashes, formula identity, and aggregate content identity while keeping package identity separate.
  Declare reference provenance and audit metadata and roster generator, namespace, ID-scheme, seed,
  configuration, and reference-package identity as profile extensions.
- Publish a fully synthetic, redistributable golden package with known hashes and at least one
  expected joined player record for cross-repository conformance.
- Publish paired synthetic reference- and roster-profile fixtures that exercise every shared field
  and prove their common values serialize identically. The roster fixture remains the self-contained
  cross-repository NBA-GM fixture.
- Document the ownership boundary in
  [NBA_GM_MVP_HANDOFF.md](../NBA_GM_MVP_HANDOFF.md): player-generator owns generation and package
  integrity; NBA-GM independently validates and consumes the MVP values and owns league context and
  simulation-specific transformations.

## Out of scope

- Generator or publication changes, which belong to US-017.
- NBA-GM implementation.
- New source fields, ESPN-derived simulation statistics, deeper metrics, personality data, and the
  review workbook.

## Validation

- Contract tests cover ordered headers, types, nulls, bounds, duplicate players, missing or extra
  rows, exact player-key sets, and representative season-ending-year values.
- Cross-profile tests strip only declared key prefixes and fail for any drift in shared ordered
  fields, types, semantic metadata, units, bounds, or serialization and for any undeclared
  null-rule difference. Tests accept only declared availability-based null overrides and reject all
  other undeclared fields and profile overrides.
- Cross-profile tests compare the common manifest envelope and file-entry definitions and reject
  undeclared profile metadata.
- The synthetic golden package passes the contract and package-integrity validators.
- Tampered headers, manifest hashes, row counts, relationships, and invalid seasons fail with
  actionable errors.
- Documentation links and `git diff --check` pass.

## Implementation notes

- **2026-07-15:** Established the cross-project format as player data contract version 1 and removed
  package-history framing from the normative contract. Exact machine-readable schemas, declared
  profile extensions, and paired fixtures remain active work and are being reconciled with the
  NBA-GM review story.
- **2026-07-15:** PR review confirmed that version 1 begins with a single statistics surface in both
  profiles. Reference season context and advanced metrics are columns in `player_stats.csv`; the
  reference profile contains five CSVs plus audit and manifest, and the roster profile contains three
  CSVs plus manifest. Runtime and conformance validation remain active before completion.

## Completion notes

Pending. Record the reviewed version 1 contract identity, declared profile extensions, exact
fixtures, cross-project decisions, validation results, deviations, follow-ups, decisions, and
learnings before changing status to `complete`.
