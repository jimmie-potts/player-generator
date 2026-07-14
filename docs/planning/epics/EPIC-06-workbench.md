# EPIC-06: Formula workbench

- **Status:** complete
- **Outcome:** Make formulas explainable and show immediate player-level effects of temporary edits.
- **Dependencies:** EPIC-05

## Stories

- [US-011: Inspect formulas and calculations](../user-stories/US-011-inspect-formulas.md)
- [US-012: Preview formula adjustments](../user-stories/US-012-preview-adjustments.md)
- [US-013: Compare representative players](../user-stories/US-013-compare-players.md)

## Success criteria

- A React/TypeScript client displays components, raw metrics, percentiles, contributions, and output.
- Weight, direction, and anchor edits update previews without changing active configuration.
- Tier-stratified representatives are shown by default, with search and pinning for targeted
  comparison.
- Reset and export make experimentation reversible and portable.

## Non-goals

- Editing arbitrary expressions.
- Saving presets or modifying repository configuration.
- Duplicating formula logic in TypeScript.

## Risks

- Fast UI feedback can mask stale or failed API calculations if request state is not explicit.
- Ranking deltas need stable baseline and preview cohorts to be meaningful.

## Implementation notes

- **2026-07-14:** Started after EPIC-05 and US-010 were merged and verified complete. The approved
  designer workflow tunes existing component weights, directions, and rating anchors only. Its
  default comparison uses three representatives from each populated talent tier, reserves room for
  ten session-only pins within the 25-player preview bound, and exports the exact server-validated
  formula document with a designer-supplied formula version.

## Completion notes

- **Completed:** 2026-07-14 in
  [PR #11](https://github.com/jimmie-potts/player-generator/pull/11), beginning with implementation
  commit `6849209`.
- **Outcome:** The local React workbench now explains every active player attribute, previews only
  approved session edits through the shared Python evaluator, compares deterministic players across
  the full talent curve, supports targeted session pins, and exports the exact validated proposal
  JSON. It never calculates ratings or persists active configuration in the browser.
- **Validation:** All 376 Python tests, 35 frontend tests, Ruff, the production TypeScript/Vite
  build, integrity manifest, and diff checks pass. A clean `npm ci` also verifies the Node 22.12 CI
  dependency layout. The real Vite proxy and preview API were exercised against the ignored
  582-player 2026 package; its 15-player adjusted preview completed in 191 ms.
- **Decisions and learnings:** [D-026](../DECISIONS.md#d-026-server-authoritative-designer-proposals-and-tiered-comparison)
  and [D-027](../DECISIONS.md#d-027-session-scoped-client-state-with-cancellable-authoritative-previews)
  define the server-authoritative, tiered, session-only workflow. Reusable findings are recorded for
  [US-011](../LEARNINGS.md#2026-07-14--us-011),
  [US-012](../LEARNINGS.md#2026-07-14--us-012), and
  [US-013](../LEARNINGS.md#2026-07-14--us-013).
- **Remaining roadmap:** EPIC-07's future player-adjacent contract definitions remain unstarted.
  Authentication, persistence, approval, deployment, arbitrary formulas, and generated team or
  coach data are not part of this epic.
