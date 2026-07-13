# US-007: Calculate the initial attribute set

- **Status:** complete
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

- **Completed:** 2026-07-13 in commit `a6fdd3b`.
- **Delivered:** the exact version `1.0.0` output schema, 13 initial attribute formulas, shooting
  priors, season cohort, 20-game/500-minute eligibility, skill and overall anchors, impact
  percentile, and tier ranges are documented and locked by automated contract tests. Snapshot
  coverage includes a star, starter, outside specialist, below-threshold row, null-overall row, and
  fully reconstructable explanations.
- **Calibration:** no rating change was approved or introduced. A comparison against the ignored
  prior processed baseline found zero mismatches across the 12 skills, overall,
  `impactPercentile`, and `talentTier`. The 2026 eligible cohort remains 376 rows with mean overall
  `67.912234`; its tiers remain 194 fringe, 98 rotation, 52 starter, 21 all-star, and 11 superstar.
- **Reviewed examples:** Jalen Duren remains `95`, `0.9946808511`, `superstar`; Giannis
  Antetokounmpo remains `87`, `0.9521276596`, `all_star`. The results reflect ranks 374 and 358 in
  the 376-row overall composite cohort. The prior counterintuitive gap is explained most clearly by
  the 8% availability contribution, approximately `0.0566` versus `0.0044`. A synthetic 376-row
  regression asserts those rank-to-output mappings without committing source rows or IDs.
- **Deviation:** the active version `1.0.0` resource was added with US-006 because a real formula
  was required to integrate the evaluator. US-007 separately reviewed and locked its calibration;
  no later attribute or consumer was pulled forward.
- **Validation:** `.venv/bin/python -m pytest` (`186 passed`), `.venv/bin/python -m ruff check .`,
  `git diff --check`, `sha256sum -c FILE_MANIFEST.sha256`, and `reference-data build` passed.
- **Follow-ups:** unsupported play-style, physical, foul, and tendency attributes remain absent.
  US-008 may now consume a published reference package through this formula version.
- **Learnings:** rank-only synthetic cohorts can preserve public calibration expectations without
  redistributing reference rows; explanation regressions should reconstruct derived metrics as
  well as contributions; and overall/tier interpretation must retain cohort size and availability
  context. These findings are recorded in
  [LEARNINGS.md](../LEARNINGS.md#2026-07-13--us-007).
