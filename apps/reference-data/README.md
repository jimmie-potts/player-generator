# Reference-data application

This Python application owns local source registration, source-specific adapters, reconciliation,
canonical normalization, the legacy rating path, and processed reference outputs.

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

Its configuration boundary is `config/default.yaml` within this application. Raw, registered, and
processed named data remain local and untracked. The remote download and wide CSV outputs are
transitional legacy behavior retained until the roster generator consumes the normalized package.
The canonical model already produces validated relational tables and audit records in memory;
`publish` writes the six version 1 relational CSVs, deterministic audit and integrity metadata, and
a package manifest to the ignored `reference_data/packages/reference-v1` directory by default. It
stages and validates the complete package before replacing an existing destination atomically.

The application may import `player_data_contracts` and `player_attribute_engine`. It must never
import `roster_generator`.
