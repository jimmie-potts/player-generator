# Version 2 redesign

This directory is the implementation plan for separating reference-data construction, roster
generation, and formula exploration. It describes a planned clean break from the current Python
pipeline; it does not describe work that has already been implemented.

## Planned architecture

```text
apps/
  reference-data/       Local Parquet ingestion and normalized reference CSVs
  roster-generator/     Player-only roster package generation
  formula-workbench/    React client and Python preview API

packages/
  data-contracts/       Versioned CSV schemas and validators
  attribute-engine/     Shared declarative formula evaluation
```

The applications share contracts and formula evaluation, but remain independently runnable. The
reference-data application must not depend on roster generation. The roster generator consumes a
published reference package rather than upstream source files.

## Delivery order

1. [EPIC-01: Repository structure and terminology](epics/EPIC-01-project-structure.md)
2. [EPIC-02: Reference-data builder](epics/EPIC-02-reference-data.md)
3. [EPIC-03: Declarative player attributes](epics/EPIC-03-attributes.md)
4. [EPIC-04: Player roster package](epics/EPIC-04-roster-package.md)
5. [EPIC-05: Formula preview API](epics/EPIC-05-formula-api.md)
6. [EPIC-06: Formula workbench](epics/EPIC-06-workbench.md)
7. [EPIC-07: Future domain contracts](epics/EPIC-07-domain-contracts.md)

EPIC-01 through EPIC-04 form the batch-data foundation. EPIC-05 and EPIC-06 add an interactive
view over the same formula engine. EPIC-07 defines future interfaces only and does not authorize
team or coach generation.

## User story index

All stories begin in `ready` status.

| ID | Story | Epic |
|---|---|---|
| US-001 | [Establish the monorepo boundaries](user-stories/US-001-monorepo-boundaries.md) | EPIC-01 |
| US-002 | [Adopt neutral domain terminology](user-stories/US-002-neutral-terminology.md) | EPIC-01 |
| US-003 | [Register local Parquet inputs](user-stories/US-003-local-parquet-inputs.md) | EPIC-02 |
| US-004 | [Normalize sources into a canonical model](user-stories/US-004-canonical-normalization.md) | EPIC-02 |
| US-005 | [Publish normalized reference CSVs](user-stories/US-005-reference-csv-package.md) | EPIC-02 |
| US-006 | [Define declarative formulas](user-stories/US-006-declarative-formulas.md) | EPIC-03 |
| US-007 | [Calculate the initial attribute set](user-stories/US-007-initial-attributes.md) | EPIC-03 |
| US-008 | [Consume a published reference package](user-stories/US-008-consume-reference-package.md) | EPIC-04 |
| US-009 | [Generate the normalized roster package](user-stories/US-009-generate-roster-package.md) | EPIC-04 |
| US-010 | [Provide formula and player preview endpoints](user-stories/US-010-formula-preview-api.md) | EPIC-05 |
| US-011 | [Inspect formulas and calculations](user-stories/US-011-inspect-formulas.md) | EPIC-06 |
| US-012 | [Preview formula adjustments](user-stories/US-012-preview-adjustments.md) | EPIC-06 |
| US-013 | [Compare representative players](user-stories/US-013-compare-players.md) | EPIC-06 |
| US-014 | [Define coach and team contracts](user-stories/US-014-coach-team-contracts.md) | EPIC-07 |

## Planning records

- [User story workflow](USER_STORY_WORKFLOW.md)
- [Decisions](DECISIONS.md)
- [Learnings](LEARNINGS.md)
- [Proposed data contracts](DATA_CONTRACTS.md)
- [Proposed attribute formulas](ATTRIBUTE_FORMULAS.md)

## Current-state warning

The repository still contains the version 1 implementation under `src/player_generator/`, with its
existing CLI, configuration, and output paths. Until a story is marked complete, those files remain
the source of truth for current behavior. Planning documents use the version 2 names and must not be
used as evidence that the corresponding code exists.
