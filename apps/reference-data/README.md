# Reference-data application

This Python application owns local source registration, source-specific adapters, reconciliation,
canonical normalization, and processed reference outputs. Its current wide build invokes the shared
declarative attribute engine as a legacy compatibility path.

```bash
reference-data --help
reference-data register --source-type nba_playerstats /path/to/playerstats.parquet
reference-data register --source-type espn_player_details /path/to/player-details.parquet
reference-data publish
reference-data publish --output /path/to/reference-v1
reference-data download
reference-data build
```

Registration validates local Parquet files without copying them. Adapter schema version 1 supports
`nba_playerstats` and `espn_player_details`; the conservative ESPN contract requires only `id` and
`displayName`, leaving unobserved bio fields optional. The ignored local registry records source
paths, IDs, hashes, adapter versions, row counts, processing timestamps, and supplied upstream or
license metadata in `reference_data/registry/sources.json`.
Registered files are referenced in place and must remain unchanged. Before and after normalization,
`publish` verifies each file's SHA-256 hash and row count against the registry; missing or changed
inputs fail publication with guidance to restore the file or rebuild its local registration.

Its application configuration boundary is `config/default.yaml`; formula weights, eligibility,
anchors, schedules, and tier ranges live only in the packaged attribute formula. Raw, registered, and
processed named data remain local and untracked. The remote download and wide CSV outputs remain
standalone legacy behavior and are not consumed by the normalized roster generator.
The canonical model already produces validated relational tables and audit records in memory;
`publish` writes the six version 1 relational CSVs, deterministic audit and integrity metadata, and
a package manifest to the ignored `reference_data/packages/reference-v1` directory by default. It
stages and validates the complete package before replacing an existing destination atomically.

The application may import `player_data_contracts` and `player_attribute_engine`. It must never
import `roster_generator`.
