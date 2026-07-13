# US-001: Establish the monorepo boundaries

- **Status:** ready
- **Epic:** [EPIC-01](../epics/EPIC-01-project-structure.md)
- **Dependencies:** none

## User story

As a contributor, I want reference building, roster generation, and formula exploration isolated so
that each responsibility can evolve and be tested independently.

## Acceptance criteria

- Create independently runnable `reference-data`, `roster-generator`, and `formula-workbench`
  applications in one repository.
- Treat reference data and roster generation as the two data subprojects; the workbench and API are
  supporting applications over their shared contracts and formula engine.
- Put versioned schemas and validation in `data-contracts` and shared calculation behavior in
  `attribute-engine`.
- Reference-data code does not import roster-generation code.
- Roster generation consumes only a published reference package.
- Each application has its own entry point, configuration boundary, tests, and documentation.
- Root commands can run each application and the complete test suite from a fresh checkout.
- Current version 1 behavior remains clearly labeled until it is replaced.

## Out of scope

- New source adapters, output schemas, formulas, or UI behavior.
- Compatibility wrappers for version 1 commands or paths.

## Validation

- Import-boundary tests fail on prohibited dependencies.
- Clean-install tests exercise each application entry point.
- Documentation link and command checks pass.

## Implementation notes

Append dated notes here while the story is active.

## Completion notes

Pending. Complete this section using the requirements in
[USER_STORY_WORKFLOW.md](../USER_STORY_WORKFLOW.md) before changing status to `complete`.
