# US-006: Define declarative formulas

- **Status:** in_progress
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
- The batch generator and preview API import the same evaluator.
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

Pending. Record the final formula contract, evaluator interface, validation behavior, commands, and
learnings before changing status to `complete`.
