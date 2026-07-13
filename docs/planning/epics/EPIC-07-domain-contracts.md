# EPIC-07: Future domain contracts

- **Status:** ready
- **Outcome:** Define stable coach and team CSV targets without generating or populating them.
- **Dependencies:** EPIC-01 and shared contract conventions

## Story

- [US-014: Define coach and team contracts](../user-stories/US-014-coach-team-contracts.md)

## Success criteria

- Coach and team schemas are documented, versioned, and machine-validatable.
- IDs, scales, dates, roles, and team membership semantics are unambiguous.
- The contracts are explicitly marked as future interfaces and do not expand the player-only roster
  release.

## Non-goals

- Generating teams or coaches.
- Team roster assignment.
- Contract and salary records, which require a separate future planning decision.

## Risks

- Prematurely detailed fields may constrain later simulation design without supporting data.
