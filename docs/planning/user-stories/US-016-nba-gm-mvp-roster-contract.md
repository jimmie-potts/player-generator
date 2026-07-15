# US-016: Define the NBA-GM MVP roster contract

- **Status:** ready
- **Epic:** [EPIC-08](../epics/EPIC-08-nba-gm-mvp-handoff.md)
- **Dependencies:** US-009 and versioned contract conventions from US-005

## User story

As an NBA-GM integrator, I want a finalized player-package contract and synthetic fixture so that
producer and consumer work can proceed independently against the same interface.

## Acceptance criteria

- Define and version a machine-readable roster contract whose exact package contains
  `players.csv`, `player_stats.csv`, `player_attributes.csv`, and `manifest.json`. The version is an
  interface identifier; no compatibility wrapper or dual publication is required before the first
  NBA-GM integration.
- Define roster `player_stats.csv` as the current traditional-stat header followed by the current
  advanced-stat fields, excluding duplicate `playerId` and `season` columns.
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
- Publish a fully synthetic, redistributable golden package with known hashes and at least one
  expected joined player record for cross-repository conformance.
- Document the ownership boundary in
  [NBA_GM_MVP_HANDOFF.md](../NBA_GM_MVP_HANDOFF.md): player-generator owns generation and package
  integrity; NBA-GM independently validates and consumes the MVP values and owns league context and
  simulation-specific transformations.

## Out of scope

- Generator or publication changes, which belong to US-017.
- NBA-GM implementation.
- New source fields, ESPN-derived simulation statistics, deeper metrics, personality data, and the
  review workbook.
- Changes to the reference package's normalized table boundaries.

## Validation

- Contract tests cover ordered headers, types, nulls, bounds, duplicate players, missing or extra
  rows, exact player-key sets, and representative season-ending-year values.
- The synthetic golden package passes the contract and package-integrity validators.
- Tampered headers, manifest hashes, row counts, relationships, and invalid seasons fail with
  actionable errors.
- Documentation links and `git diff --check` pass.

## Implementation notes

Append dated notes here while the story is active. Reconcile the final contract and fixture with the
NBA-GM review story before changing publication behavior.

## Completion notes

Pending. Record the reviewed contract identifier, exact fixture, cross-project decisions,
validation results, deviations, follow-ups, decisions, and learnings before changing status to
`complete`.
