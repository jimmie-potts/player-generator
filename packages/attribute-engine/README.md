# Attribute-engine package

This package owns the shared declarative player-attribute engine. The active formula document is
`player-attributes-v1.json`, declares formula version `1.0.0`, and is packaged with the Python
distribution. `data-contracts` owns its structural schema; this package owns semantic validation,
supported metric derivations, percentile evaluation, explanations, and talent-tier assignment.

The public API is application-independent:

```python
from player_attribute_engine import evaluate_player_attributes, load_formula

formula = load_formula()
batch = evaluate_player_attributes(joined_rows, formula)
```

Package publishers can call `load_formula_snapshot()` to parse a document and hash the exact same
byte snapshot for integrity metadata. Read-only consumers that also need to expose or temporarily
edit the declarative payload can call `load_formula_payload_snapshot()` to receive the raw JSON,
parsed document, and hash from that one immutable read.

The evaluator accepts one season cohort as an in-memory `pandas.DataFrame` whose camelCase fields
come from a joined reference or roster player-season. A caller with multiple seasons evaluates each
cohort separately; the current legacy adapter performs that grouping. The evaluator does not read
packages, Parquet, application configuration, or paths. `EvaluationBatch.rows` follows the
formula's exact output field order, while
`EvaluationBatch.explanations` records eligibility, cohort, raw component values, component
percentiles, normalized weights, contributions, the weighted composite, its percentile, and the
final rating.

Callers that do not need every explanation can pass `explanation_player_ids`. The evaluator still
calculates every cohort row, percentile, and rating, but materializes explanation objects only for
the requested IDs and returns them in cohort order. Omitting the option preserves all explanations;
an empty collection returns none, and an unknown ID fails evaluation.

Formula schema version 1 supports only declared input metrics and three whitelisted derivations:
ratios, shooting percentages stabilized toward the full season's league average, and scheduled-game
ratios. Unknown fields, arbitrary expressions, unsupported schema versions, invalid weights,
directions, anchors, dependencies, or tier ranges fail before evaluation.

Input columns accept only finite real numeric scalars or nulls; strings, booleans, complex values,
and temporal values are rejected rather than coerced. Schedule keys are canonical four-digit season
years, and metric aliases always read from the original input snapshot so document key order cannot
change a result.

Deterministic version 1 rules are:

- null component or eligibility values exclude that row from the affected formula;
- minimum samples are 20 games and 500 minutes;
- cohorts group by season, and shooting priors use the full season before eligibility filtering;
- ties use average ranks and pandas `rank(pct=True)` semantics, including a singleton percentile of
  `1.0`;
- lower-is-better components reverse the rank direction;
- ratings interpolate through declared 25–99 anchors and use half-even rounding;
- talent tiers come only from the active formula's versioned overall ranges.

The current legacy `reference-data build` delegates to this evaluator through
`rate_player_seasons`. Normalized reference publication and roster generation evaluate their season
cohorts through the public API instead of that wide-table adapter. The formula preview API also
evaluates its complete configured reference cohort through this API for both its cached baseline and
temporary request-local previews; its HTTP layer does not implement another calculation path.
