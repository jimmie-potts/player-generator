# US-011: Inspect formulas and calculations

- **Status:** complete
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

- **Completed:** 2026-07-14 in
  [PR #11](https://github.com/jimmie-potts/player-generator/pull/11), beginning with implementation
  commit `6849209`.
- **Delivered:** Replaced the static shell with a typed React client that loads formula, metric,
  player, and calculation data from `/api/v1`. The attribute rail, formula inspector, and calculation
  inspector expose every declared component and rule plus API-returned raw inputs, percentiles,
  normalized weights, contributions, composites, ratings, overall, and talent tier. Missing,
  excluded, unsupported, loading, empty, stale-context, and request-error states have distinct copy
  and presentation, and prior calculation results are cleared while their replacement is pending or
  after it fails.
- **Architecture and accessibility:** The browser contains editor diffing and display formatting but
  no rating, percentile, or ranking implementation. It verifies complete API context identities
  before combining responses. Semantic navigation, labeled form controls, table headers, keyboard-
  focusable overflow regions, and live loading/error states keep the dense inspection surface
  operable without relying only on color.
- **Deviations and decisions:** No inspection acceptance criterion was removed. The typed client and
  context/cancellation boundary are recorded in
  [D-027](../DECISIONS.md#d-027-session-scoped-client-state-with-cancellable-authoritative-previews).
  Editing and comparison were delivered in the same integrated epic but remain owned by US-012 and
  US-013.
- **Validation:** `.venv/bin/python -m pytest` passed 376 tests;
  `.venv/bin/python -m ruff check .`, `npm run workbench:build`, and `git diff --check` passed;
  `npm run workbench:test` passed 35 tests. Rendered integration coverage verifies the complete
  initial API flow and exact contribution cells, while focused tests cover context mismatches and
  missing calculation values.
- **Follow-ups:** Authentication, persistence, proposal approval, deployment, and arbitrary formula
  expressions remain outside the implemented inspection boundary.
- **Learnings:** Calculation metadata and shared-engine explanation trees are sufficient for a fully
  explainable browser without a second evaluator, while context comparison must happen before
  otherwise valid endpoint responses are combined. These findings are recorded in
  [LEARNINGS.md](../LEARNINGS.md#2026-07-14--us-011).
