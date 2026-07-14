# US-011: Inspect formulas and calculations

- **Status:** in_progress
- **Epic:** [EPIC-06](../epics/EPIC-06-workbench.md)
- **Dependencies:** US-010

## User story

As a designer, I want to inspect each attribute formula and player calculation so that rating
outcomes are explainable.

## Acceptance criteria

- Build a TypeScript React workbench that loads formula and player data from the preview API.
- List every supported attribute with components, metric descriptions, direction, weights,
  eligibility, cohort, anchors, scale, and formula version.
- Selecting a player shows raw metrics, component percentiles, normalized weights, contributions,
  composite percentile, final rating, overall, and tier where applicable.
- Missing, excluded, and unsupported metrics are visually distinct and explained.
- Loading, empty, stale-version, and API-error states do not display prior results as current.
- The client contains no independent rating calculation implementation.

## Out of scope

- Editing or previewing formulas; that is US-012.

## Validation

- Component tests cover attribute selection, player detail, missing inputs, errors, and version
  display.
- An integration test verifies rendered contributions match the API fixture exactly.

## Implementation notes

- **2026-07-14:** Dependency US-010 is complete. Started the API-backed React inspection surface
  with API-owned data as the only source for formula metadata, player calculations, and context
  identity. Loading, empty, stale-context, and request failures will clear or label prior data rather
  than presenting it as current.

## Completion notes

Pending. Record UI structure, accessibility checks, test commands, and user-facing learnings before
changing status to `complete`.
