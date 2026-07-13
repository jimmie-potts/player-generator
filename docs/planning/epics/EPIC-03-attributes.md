# EPIC-03: Declarative player attributes

- **Status:** complete
- **Outcome:** Calculate explainable, versioned player attributes through one shared engine.
- **Dependencies:** EPIC-02

## Why

Before this epic, formula definitions lived in Python and could not be safely inspected or adjusted
by a web client. Batch generation and interactive previews need the same evaluator.

## Stories

- [US-006: Define declarative formulas](../user-stories/US-006-declarative-formulas.md)
- [US-007: Calculate the initial attribute set](../user-stories/US-007-initial-attributes.md)

## Success criteria

- Formulas declare components, direction, weights, eligibility, anchors, and version.
- The engine produces deterministic 25–99 ratings and explainable intermediate values.
- Percentile cohorts, nulls, ties, sample thresholds, overall, impact percentile, and tiers have
  regression coverage.
- Attributes lacking defensible inputs remain deferred.

## Non-goals

- Executing arbitrary user expressions.
- Persisting formula edits from the workbench.
- Creating attributes whose source requirements are unavailable.

## Risks

- Double-ranking and cohort selection can produce unintuitive superstar and tier assignments.
- Missing values can change the evaluated population unless eligibility is explicit.
