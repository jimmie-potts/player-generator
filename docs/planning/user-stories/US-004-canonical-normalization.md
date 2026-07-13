# US-004: Normalize sources into a canonical model

- **Status:** in_progress
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

### 2026-07-13

- Started after US-003 completed in commit `1324e9b`; normalization consumes only validated local
  registry entries and source-owned adapters.
- Selected deterministic opaque internal IDs, conservative exact-name reconciliation, reviewed
  source-ID overrides, and configured field precedence. Fuzzy or probabilistic matching remains
  outside this story.
- Preserved the aggregate season grain: canonical team identity is populated only when the NBA
  source explicitly reports a single-team aggregate, while all source team labels remain audit
  context.
- Added source-owned mappings for player bio, aggregate season context, traditional statistics, and
  advanced statistics. ESPN version 1 maps only optional fields whose names declare their meaning
  and units; ambiguous `height` and `weight` fields remain unavailable.
- Reconciliation treats source IDs as namespaced, collapses repeated IDs across seasons, applies
  reviewed overrides before conservative normalized exact-name matching, and gives ambiguous or
  unmatched identities separate stable players with explicit audit outcomes.
- Canonical players and player-seasons use deterministic opaque UUID-derived IDs. Per-field source
  precedence and latest-season tie-breaking are configured, nulls fall through to the next source,
  and every distinct non-null conflict records its candidates, chosen value, and rule.
- Focused validation covered 28 adapter and canonical cases; the full reference-data suite passed
  46 tests. A local ignored 6,908-row NBA source normalized into 1,693 players and matching sets of
  6,908 season, traditional-stat, and advanced-stat rows without changing or copying the input.

## Completion notes

Pending. Record reconciliation outcomes, precedence rules, unresolved source gaps, and validation
evidence before changing status to `complete`.
