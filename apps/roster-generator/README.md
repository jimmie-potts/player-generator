# Roster-generator application

This Python application owns published-reference validation, deterministic template selection,
controlled statistics mutation, generated player identity, shared-engine attribute evaluation, and
atomic roster-package publication.

```bash
roster-generator --help
roster-generator generate
roster-generator generate --reference-package /path/to/reference-v1
roster-generator generate --output /path/to/roster-v1 --seed 42
```

Its YAML configuration makes eligible seasons, recency weights, games/minutes thresholds, roster
size, sampling replacement, seed, and mutation controls explicit. CLI options may override the
reference package, formula document, output directory, and seed.

The application validates the complete reference manifest, files, hashes, row counts, contract
versions, relationships, and formula compatibility before sampling. It mutates primitive totals,
derives dependent statistics, calculates attributes through `player_attribute_engine`, validates
the four version 1 roster CSVs, scans for reference identity leakage, and replaces the destination
only after staging succeeds.

The application may import shared data-contract and attribute-engine code. It must never import
`reference_data_app`, read Parquet, generate teams or coaches, or publish a template crosswalk.
