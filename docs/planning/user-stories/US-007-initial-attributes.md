# US-007: Calculate the initial attribute set

- **Status:** in_progress
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

### 2026-07-13

- Started after US-006 completed in commit `201c3f7`.
- Formula version `1.0.0` already contains the documented initial attributes because the active
  declarative resource was needed to validate and integrate US-006. This story now locks that
  calibration with exact contract assertions, tier boundaries, representative snapshots, and
  named-outcome regressions.
- Regression cohorts are generated from synthetic rows. No source IDs, names, or third-party raw
  values are copied into tracked fixtures; ignored local reference data is used only to compare the
  new evaluator with the prior generated baseline.

## Completion notes

Pending. Record calibration changes, reviewed player examples, distribution effects, commands, and
learnings before changing status to `complete`.
