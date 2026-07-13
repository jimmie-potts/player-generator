# EPIC-06: Formula workbench

- **Status:** ready
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
