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

The evaluator accepts one season cohort as an in-memory `pandas.DataFrame` whose camelCase fields
come from a joined reference or roster player-season. A caller with multiple seasons evaluates each
cohort separately; the current legacy adapter performs that grouping. The evaluator does not read
packages, Parquet, application configuration, or paths. `EvaluationBatch.rows` follows the
formula's exact output field order, while
`EvaluationBatch.explanations` records eligibility, cohort, raw component values, component
percentiles, normalized weights, contributions, the weighted composite, its percentile, and the
final rating.

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
`rate_player_seasons`. US-008 will replace that wide-table compatibility adapter, and US-010 must
import this same evaluator for previews rather than implementing another calculation path.
