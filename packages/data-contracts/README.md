# Data-contracts package

This Python package owns shared versioned schema resources, keys, scalar types, relationships,
rating-field identifiers, tier ordering, and validation for data exchanged between applications.

Packaged contract resources are:

- `schemas/reference-v1.schema.json`: the ordered headers, required and nullable fields, scalar
  types, unique keys, and relationships for the six normalized reference CSVs.
- `schemas/formula-v1.schema.json`: the structural contract for versioned declarative player
  formulas, including their required sections, supported metric shapes, and 25–99 rating bounds.
- `schemas/roster-v1.schema.json`: the current combined roster JSON interface.

Reference-package producers can validate native row mappings before serialization and then validate
the staged CSV directory before publication:

```python
from player_data_contracts import validate_reference_package, validate_reference_tables

validate_reference_tables(tables)
validate_reference_package(staged_package_dir)
```

`load_reference_contract()` exposes the machine-readable reference version 1 definition.
`load_formula_contract()` exposes the machine-readable formula version 1 definition; the
attribute-engine adds the semantic checks that depend on the supported metric vocabulary and
cross-references within a formula document. Reference validation requires
exact ordered CSV headers, empty optional values, finite numbers, ISO 8601 dates and timezone-aware
timestamps, unique keys, player relationships, registered source types, and identical aggregate
player-season key sets across the season, traditional-stat, and advanced-stat tables.

The normalized roster CSV contracts remain planned for US-009.
