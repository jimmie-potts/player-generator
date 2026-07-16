# US-014: Define coach and team contracts

- **Status:** ready
- **Epic:** [EPIC-07](../epics/EPIC-07-domain-contracts.md)
- **Dependencies:** US-001 and versioned contract conventions from US-005

## User story

As a future roster-system developer, I want approved coach and team schemas so that later generation
work has stable integration targets.

## Acceptance criteria

- Define and version machine-readable contracts for `coaches.csv` and `teams.csv` using the headers
  in [DATA_CONTRACTS.md](../DATA_CONTRACTS.md).
- Document required and optional fields, types, uniqueness, enums, nullability, and relationships.
- Use stable opaque nonempty `coachId` and `teamId` values that are unique within their NBA-GM-owned
  league context and joined by exact string equality; do not require a global namespace, UUIDs, or a
  cross-project crosswalk. Reference team membership through `teamId` rather than embedded roster
  arrays.
- Use ISO 8601 dates and 0–100 coach ratings or preference scales.
- Define supported coach roles and the meaning of system, pace, rotation, market, and prestige
  fields without inventing population rules.
- Validate representative empty and populated fixtures.
- Mark both contracts as future design targets that are not emitted by the player-only roster
  generator.

## Out of scope

- Populating or generating teams and coaches.
- Player-team assignment, coach effects, schedules, contracts, salary, or cap rules.

## Validation

- Schema tests cover valid rows, duplicate IDs, invalid enums, out-of-range values, invalid dates,
  and unknown team references.

## Implementation notes

Append dated notes here while the story is active.

## Completion notes

Pending. Record schema versions, reviewed semantics, fixture tests, deferred questions, and learnings
before changing status to `complete`.
