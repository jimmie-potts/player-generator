# US-006: Define declarative formulas

- **Status:** complete
- **Epic:** [EPIC-03](../epics/EPIC-03-attributes.md)
- **Dependencies:** US-005

## User story

As a designer, I want formulas stored as validated data so that batch generation and interactive
previews use exactly the same calculations.

## Acceptance criteria

- A versioned YAML or JSON contract declares each attribute's metrics, weights, direction,
  eligibility requirements, percentile cohort, anchors, output scale, and formula version.
- Component weights are finite and nonnegative, have a positive sum, and normalize to 1.
- Percentile anchors are ordered, cover 0 and 1, and map monotonically to the 25–99 scale.
- Unknown metrics, duplicate components, invalid directions, invalid anchors, and unavailable
  required inputs fail before evaluation.
- Null handling, ties, inverse metrics, and minimum-sample eligibility have documented deterministic
  rules.
- Evaluation returns raw inputs, component percentiles, normalized weights, contributions,
  composite percentile, and final rating.
- Every implemented batch or preview calculation path imports the shared evaluator. The current
  batch path does; per [D-017](../DECISIONS.md#d-017-shared-evaluator-consumer-sequencing), this is
  a binding acceptance constraint on the preview API when US-010 implements it.
- Arbitrary code or expression execution is not supported.

## Out of scope

- Formula persistence through the web application.

## Validation

- Unit tests cover every validation rule and deterministic calculation stage.
- Golden formula documents demonstrate forward rejection of unsupported schema versions.

## Implementation notes

### 2026-07-13

- Started after US-005 and EPIC-02 were completed and merged in PR #4.
- The formula contract and evaluator are owned by `packages/attribute-engine`; the current
  reference-data wide-table build may call that shared engine, but migration of the roster
  generator to normalized reference packages remains US-008 work and the preview API remains
  US-010 work.
- Declarative formulas are restricted to a supported schema and metric vocabulary. They do not
  permit Python expressions or arbitrary code execution.
- Formula schema version 1 is a packaged data contract. The attribute engine adds semantic
  validation for metric dependencies, weights, directions, named eligibility/cohort/scale
  references, anchors, output fields, and talent-tier coverage before evaluation.
- Formula version `1.0.0` moves the weights, 20-game/500-minute eligibility, season schedules,
  shooting priors, percentile anchors, and tier ranges out of application YAML. Only input,
  ratio, stabilized-percentage, and scheduled-ratio metrics are supported.
- The current reference-data wide build now delegates to the shared evaluator. Stabilized shooting
  league averages are derived from the full season before formula eligibility filters rows, which
  preserves the implemented baseline while making the order explicit.
- Explanations are JSON-serializable and include the cohort, eligibility outcome, raw component
  values, percentiles, normalized weights, contributions, composite, composite percentile, and
  rating. The future preview API can consume the same result without another evaluator.
- [D-017](../DECISIONS.md#d-017-shared-evaluator-consumer-sequencing) records that US-010 must
  import this evaluator when it introduces the preview API; implementing that later API in this
  story would violate the planned delivery order.

## Completion notes

- **Completed:** 2026-07-13 in commit `201c3f7`.
- **Pull request:** [#5](https://github.com/jimmie-potts/player-generator/pull/5).
- **Review hardening:** commit `c37bb63` added overflow-safe weight normalization, immutable input
  alias reads, canonical schedules with shared explanation lookup, strict numeric input types, and
  load-time validation of the shooting-season dependency. Commit `f3d319b` preserved homogeneous
  temporal null columns as null rather than allowing Pandas' integer sentinel into evaluation.
- **Delivered:** packaged formula contract version 1 and active formula version `1.0.0`; typed
  semantic validation; a public, application-independent evaluator returning ordered rows and
  reconstructable JSON explanations; and migration of the current reference-data batch seam to
  the shared evaluator.
- **Failure behavior:** unsupported schema/reference versions, unknown or cyclic metrics, invalid
  numeric values, weights, directions, anchors, schedules, tiers, output collisions, missing input
  fields, mixed cohorts, and invalid player IDs fail before ratings are returned. Formula documents
  support only the four declared metric kinds and cannot execute expressions or code.
- **Deviation:** the preview API does not exist until US-010. Per
  [D-017](../DECISIONS.md#d-017-shared-evaluator-consumer-sequencing), this story exported the
  evaluator that US-010 must import instead of implementing the later API early.
- **Validation:** `.venv/bin/python -m pytest` (`195 passed` after final review) and
  `.venv/bin/python -m ruff check .` passed, as did `git diff --check`,
  `sha256sum -c FILE_MANIFEST.sha256`, and the current `reference-data build` against ignored local
  inputs. The formula schema and active formula resources were also confirmed in a built wheel.
- **Follow-ups:** US-007 locks the initial attribute calibration and representative regressions;
  US-008 replaces the current wide-table batch seam; US-010 imports this evaluator for previews.
- **Learnings:** structural schema validation and semantic graph validation are complementary;
  derived-metric policy belongs to the formula version; full-cohort shooting priors must precede
  formula eligibility; and consumer-independent evaluation requires package/path loading to stay
  outside the engine. These findings are recorded in
  [LEARNINGS.md](../LEARNINGS.md#2026-07-13--us-006).
