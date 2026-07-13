# US-004: Normalize sources into a canonical model

- **Status:** ready
- **Epic:** [EPIC-02](../epics/EPIC-02-reference-data.md)
- **Dependencies:** US-003

## User story

As a data maintainer, I want every source mapped through a canonical model so that downstream
applications do not depend on upstream schemas.

## Acceptance criteria

- Source adapters map upstream columns to canonical camelCase fields without changing metric
  meaning.
- Canonical IDs distinguish internal `playerId` and `playerSeasonId` from source IDs.
- The canonical player-season grain is one aggregate row per player and season; team IDs are set
  only when the aggregate represents one team, and multi-team source labels are retained as source
  context rather than treated as a team ID.
- Source-ID reconciliation is deterministic and supports reviewed manual overrides.
- Ambiguous and unmatched identities are reported; ambiguous matches are never auto-merged.
- Merge precedence is declared by canonical field and source type in configuration.
- Conflicting non-null values produce an audit record containing candidates and the chosen rule.
- Duplicate canonical keys, invalid types, and referential-integrity failures stop publication.
- Adding a new adapter does not require changes to roster-generation code.

## Out of scope

- Team-stint statistical publication and probabilistic identity matching.

## Validation

- Fixtures cover exact source-ID matches, manual overrides, ambiguous names, unmatched players,
  conflicts, null fallback, multi-team seasons, and duplicate keys.
- Adapter contract tests confirm equivalent source values produce the same canonical value.

## Implementation notes

Append dated notes here while the story is active.

## Completion notes

Pending. Record reconciliation outcomes, precedence rules, unresolved source gaps, and validation
evidence before changing status to `complete`.
