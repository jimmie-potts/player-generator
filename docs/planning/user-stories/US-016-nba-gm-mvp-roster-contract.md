# US-016: Define parity-aligned MVP player contracts

- **Status:** ready
- **Epic:** [EPIC-08](../epics/EPIC-08-nba-gm-mvp-handoff.md)
- **Dependencies:** US-009, US-015, and versioned contract conventions from US-005

## User story

As a player-data integrator, I want reference and roster player files to derive from shared contract
definitions, with a finalized roster fixture for NBA-GM, so producer and consumer work can proceed
independently without the two player-generator profiles drifting.

## Acceptance criteria

- Define one machine-readable contract family with reference and roster profiles for corresponding
  `players.csv`, `player_stats.csv`, and `player_attributes.csv` files. Derive every shared field
  definition from one source rather than copying it between profile schemas.
- Define and version the roster profile whose exact package contains
  `players.csv`, `player_stats.csv`, `player_attributes.csv`, and `manifest.json`. The version is an
  interface identifier; no compatibility wrapper or dual publication is required before the first
  NBA-GM integration.
- Define both profiles' `player_stats.csv` as their current traditional-stat fields followed by the
  corresponding current advanced-stat fields, excluding duplicate key columns. Retire
  `player_advanced_stats.csv` from both target profiles.
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
- Resolve the shared statistics payload so both profiles represent counts, `games`, `minutes`, the
  possession basis, percentages, and rates consistently. If reference `player_seasons.csv` retains
  a value also published in `player_stats.csv`, require exact equality rather than two independently
  mutable definitions.
- Define a common manifest envelope for package type and contract identity, file row counts and
  hashes, formula identity, and aggregate content identity. Declare reference provenance and audit
  metadata and roster generator, namespace, ID-scheme, seed, configuration, and reference-package
  identity as profile extensions.
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

Append dated notes here while the story is active. Reconcile the final contract and fixture with the
NBA-GM review story before changing publication behavior.

## Completion notes

Pending. Record the reviewed contract identifiers, declared profile extensions, exact fixtures,
cross-project decisions, validation results, deviations, follow-ups, decisions, and learnings before
changing status to `complete`.
