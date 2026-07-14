# Data-contracts package

This Python package owns shared versioned schema resources, keys, scalar types, relationships,
rating-field identifiers, and validation for data exchanged between applications.

Packaged contract resources are:

- `schemas/reference-v1.schema.json`: the ordered headers, required and nullable fields, scalar
  types, unique keys, and relationships for the six normalized reference CSVs.
- `schemas/reference-v2.schema.json`: the additive seven-file reference contract with calculated
  attributes at the aggregate player-season grain.
- `schemas/formula-v1.schema.json`: the structural contract for versioned declarative player
  formulas, including their required sections, supported metric shapes, and 25–99 rating bounds.
- `schemas/roster-v1.schema.json`: the ordered headers, null rules, bounds, keys, relationships, and
  semantic statistical invariants for the four normalized roster CSVs.

Reference-package producers can validate native row mappings before serialization and then validate
the staged CSV directory before publication:

```python
from player_data_contracts import validate_reference_package, validate_reference_tables

validate_reference_tables(tables)
validate_reference_package(staged_package_dir)
```

Roster-package producers use the equivalent APIs before and after serialization:

```python
from player_data_contracts import validate_roster_package, validate_roster_tables

validate_roster_tables(tables)
validate_roster_package(staged_package_dir)
```

`load_reference_contract()` exposes the active machine-readable reference version 2 definition;
pass version `1` to load the preserved six-file contract.
`load_formula_contract()` exposes the machine-readable formula version 1 definition; the
attribute-engine adds the semantic checks that depend on the supported metric vocabulary and
cross-references within a formula document. Reference validation requires
exact ordered CSV headers, empty optional values, finite numbers, ISO 8601 dates and timezone-aware
timestamps, unique keys, player relationships, registered source types, and identical aggregate
player-season key sets across the season-grain tables, including attributes in version 2.
`load_roster_contract()` exposes roster contract version 1. Roster validation additionally enforces
shooting decompositions, points and rebound totals, derived per-game/per-36/per-100 rates,
percentages, net ratings, advanced-stat relationships, and exact player/key sets.
Each roster player has exactly one aligned traditional-stat and advanced-stat season because the
attribute table is player-grain.
