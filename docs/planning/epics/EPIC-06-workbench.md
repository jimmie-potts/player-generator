# EPIC-06: Formula workbench

- **Status:** in_progress
- **Outcome:** Make formulas explainable and show immediate player-level effects of temporary edits.
- **Dependencies:** EPIC-05

## Stories

- [US-011: Inspect formulas and calculations](../user-stories/US-011-inspect-formulas.md)
- [US-012: Preview formula adjustments](../user-stories/US-012-preview-adjustments.md)
- [US-013: Compare representative players](../user-stories/US-013-compare-players.md)

## Success criteria

- A React/TypeScript client displays components, raw metrics, percentiles, contributions, and output.
- Weight, direction, and anchor edits update previews without changing active configuration.
- Top players are shown by default, with search and pinning for targeted comparison.
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
