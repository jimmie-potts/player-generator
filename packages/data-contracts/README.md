# Data-contracts package

This Python package owns shared versioned schema resources, keys, scalar types, relationships,
rating-field identifiers, and validation for data exchanged between applications.

The cross-project baseline is [player data contract version 1](../../docs/planning/DATA_CONTRACTS.md).
The reference and roster resources are profiles of that one contract family. The current resources
implement the version 1 inventories and profile relationships. The authored family resource now
owns the target shared field definitions, semantic metadata, profile extensions, availability
overrides, and CSV conventions. The expanded profile resources remain the current runtime and
portable consumer schemas. Their known alignment work is closed in the family resource's temporary
gap ledger, and validation fails if either profile develops an undeclared difference. US-016 remains
in progress for paired fixtures and final contract decisions; US-017 removes the declared runtime
gaps as it applies the aligned definitions to publication.

Packaged contract resources are:

- `schemas/player-data-v1.contract.json`: the one authored catalog for shared ordered fields,
  meanings, units, classifications, scalar targets, bounds, CSV formatting, profile extensions,
  availability overrides, and the exact temporary alignment ledger.
- `schemas/reference-v1.schema.json`: the ordered headers, required and nullable fields, scalar
  types, unique keys, and relationships for the five normalized reference-profile CSVs.
- `schemas/formula-v1.schema.json`: the structural contract for versioned declarative player
  formulas, including their required sections, supported metric shapes, and 25–99 rating bounds.
- `schemas/roster-v1.schema.json`: the ordered headers, null rules, bounds, keys, relationships, and
  semantic statistical invariants for the three normalized roster-profile CSVs.

Contract-family tooling exposes the shared source and verifies that the runtime profiles differ
from it only where the temporary ledger says they do:

```python
from player_data_contracts import (
    load_player_data_contract,
    validate_player_data_profile_parity,
)

family = load_player_data_contract()
validate_player_data_profile_parity()
```

`validate_player_data_profile_parity()` treats both new issues and obsolete gap declarations as
failures. Each temporary exception pins its exact current value or full shared order as well as the
target definition, so a different mismatch at an already-known location also fails. A fixed
discrepancy therefore requires removing its ledger entry in the same change.
`serialize_csv_value()` implements the family's canonical scalar representation for conformance
fixtures and later publisher adoption.

Reference-package producers can validate native row mappings before serialization and then validate
the staged CSV directory before publication:

```python
from player_data_contracts import validate_reference_package, validate_reference_tables

validate_reference_tables(tables)
validate_reference_package(staged_package_dir)
```

Applications that consume a published package can load its contract-normalized rows only after the
shared integrity boundary succeeds:

```python
from player_data_contracts import load_reference_package_tables

package = load_reference_package_tables(package_dir)
```

The loader verifies the contract version and profile, exact directory and manifest file sets,
per-file hashes and row counts, aggregate content hash, CSV contracts and relationships, audit count,
and formula provenance. It hashes every data file before and after typed reads so a package
that changes during loading is rejected. The returned object contains package identity, manifest,
contract, and normalized table rows; consumer-specific joins, formula requirements, selection, and
identity-exposure policy remain in the consuming application.

Roster-package producers use the equivalent APIs before and after serialization:

```python
from player_data_contracts import validate_roster_package, validate_roster_tables

validate_roster_tables(tables)
validate_roster_package(staged_package_dir)
```

`load_reference_contract()` exposes the machine-readable version 1 reference-profile definition.
`load_formula_contract()` exposes the machine-readable formula version 1 definition; the
attribute-engine adds the semantic checks that depend on the supported metric vocabulary and
cross-references within a formula document. Reference validation requires exact ordered CSV headers,
LF-terminated lines without carriage returns, empty optional values, finite numbers, ISO 8601 dates
and timezone-aware timestamps,
declared unique keys, player foreign keys, registered source-type membership, and identical aggregate
player-season key sets across statistics and attributes. Contract declarations are checked even when
a table has no rows, and a foreign key must target one declared unique key. `load_roster_contract()`
exposes the version 1 roster-profile definition.
Roster validation additionally enforces
shooting decompositions, points and rebound totals, derived per-game/per-36/per-100 rates,
percentages, net ratings, advanced-stat relationships, and exact player/key sets.
Each roster player has exactly one consolidated statistics row because the attribute table is
player-grain.

The formula preview API consumes these shared data and formula contracts but owns its version 1 HTTP
Pydantic models and generated OpenAPI document. Transport-only context tokens, request edits, and
error envelopes therefore do not become CSV or formula-document fields.
