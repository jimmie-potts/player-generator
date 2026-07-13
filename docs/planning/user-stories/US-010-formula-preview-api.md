# US-010: Provide formula and player preview endpoints

- **Status:** ready
- **Epic:** [EPIC-05](../epics/EPIC-05-formula-api.md)
- **Dependencies:** US-005, US-007

## User story

As a frontend developer, I want a read-only formula API so that the browser can inspect and preview
the authoritative calculations without reimplementing them.

## Acceptance criteria

- Expose versioned endpoints for the active formula document, available metric metadata, baseline
  player results, player search, player calculation detail, and temporary previews.
- Preview requests accept changed component weights, inverse direction, and percentile anchors plus
  selected player IDs.
- Preview responses include baseline value, preview value, delta, rank movement, raw inputs,
  percentiles, normalized weights, contributions, and validation errors.
- Search supports normalized partial player names and stable player IDs.
- The default baseline sample is bounded and ranked by baseline overall; requested pinned players
  can be added to it.
- Recalculation uses the shared attribute engine and an explicitly identified reference-package and
  formula version.
- Preview endpoints do not write formula configuration, reference data, or presets.
- Invalid requests return structured field-level errors without partial results.

## Out of scope

- Authentication, persistence, formula deployment, and production infrastructure.

## Validation

- API contract tests cover formulas, metrics, search, detail, previews, invalid edits, missing
  players, package mismatch, and write prevention.
- Performance tests set an approved preview latency budget for the bounded sample.

## Implementation notes

Append dated notes here while the story is active.

## Completion notes

Pending. Record endpoint contracts, sample bounds, latency results, commands, and learnings before
changing status to `complete`.
