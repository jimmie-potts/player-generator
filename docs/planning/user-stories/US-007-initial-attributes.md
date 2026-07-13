# US-007: Calculate the initial attribute set

- **Status:** ready
- **Epic:** [EPIC-03](../epics/EPIC-03-attributes.md)
- **Dependencies:** US-006

## User story

As a designer, I want an explicit initial attribute model so that every published rating can be
explained and calibrated.

## Acceptance criteria

- Implement the output schema and baseline weights in
  [ATTRIBUTE_FORMULAS.md](../ATTRIBUTE_FORMULAS.md).
- Evaluate skill percentiles within the declared season cohort and record the cohort and eligibility
  rules in the formula version.
- Calculate `impactPercentile` from the overall composite, map it to `overall` through the overall
  anchors, and derive `talentTier` only from versioned overall ranges.
- Shooting percentages retain an explicit, tested stabilization rule before percentile evaluation.
- Attributes with unsupported inputs remain absent rather than receiving placeholder calculations.
- Regression fixtures explain the prior Jalen Duren and Giannis Antetokounmpo overall,
  impact-percentile, and tier results, then assert the approved behavior under the new model.
- Generated explanations can reconstruct every component contribution and final result.

## Out of scope

- Midrange, shot creation, ball handling, help defense, speed, strength, foul discipline, and
  detailed tendencies until reviewed inputs exist.

## Validation

- Formula unit tests cover scale bounds, tier boundaries, ties, sparse cohorts, nulls, and inverse
  metrics.
- Snapshot tests compare representative stars, starters, specialists, low-minute players, and
  excluded players.

## Implementation notes

Append dated notes here while the story is active.

## Completion notes

Pending. Record calibration changes, reviewed player examples, distribution effects, commands, and
learnings before changing status to `complete`.
