# EPIC-04: Player roster package

- **Status:** complete
- **Outcome:** Generate a deterministic, normalized player-only CSV package from published
  reference data.
- **Dependencies:** EPIC-02, EPIC-03

## Why

The roster generator should depend on a versioned reference contract rather than raw Parquet or
source-specific schemas, and consumers should load player data by concern.

## Stories

- [US-008: Consume a published reference package](../user-stories/US-008-consume-reference-package.md)
- [US-009: Generate the normalized roster package](../user-stories/US-009-generate-roster-package.md)

## Success criteria

- Reference contract conformance is checked before generation.
- A fixed input package, configuration, formula version, and seed reproduce the same rows.
- Related statistical values remain internally consistent after controlled mutation.
- Roster output does not expose upstream identities or source identifiers.

## Non-goals

- Team assignment, coach generation, contracts, or league scheduling.
- Reading upstream Parquet directly.
- Filling fields without supported source inputs or approved generation rules.

## Risks

- Independent mutation can break relationships between makes, attempts, totals, and rate stats.
- Normalized files can drift unless one manifest pins every contract and input version.
