# US-006: Define declarative formulas

- **Status:** ready
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

Append dated notes here while the story is active.

## Completion notes

Pending. Record the final formula contract, evaluator interface, validation behavior, commands, and
learnings before changing status to `complete`.
