# Reference-data application

This Python application owns local source registration, source-specific adapters, reconciliation,
canonical normalization, and processed reference outputs. Its standalone wide build invokes the
shared declarative attribute engine as a legacy path.

```bash
reference-data --help
reference-data register --source-type nba_playerstats /path/to/playerstats.parquet
reference-data register --source-type espn_player_details /path/to/player-details.parquet
reference-data publish
reference-data publish --output /path/to/reference-v1
reference-data publish --formula /path/to/player-attributes.json
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

Its application configuration boundary is `config/default.yaml`. The `reference` block (`seasons`,
`comparison_season`, and `season_weights`) is consumed only by the standalone legacy `build`
command. Normalized `publish` does not filter or weight canonical cohorts with that block; it
publishes every canonical player-season supplied by the registered inputs. Publication uses the
configured registry and package paths plus the `normalization` rules. Formula weights, eligibility,
anchors, schedules, and tier ranges live only in the selected formula document. Raw, registered, and
processed named data remain local and untracked. The remote download and wide CSV outputs remain
standalone legacy behavior and are not consumed by the normalized roster generator.
The canonical model already produces validated relational tables and audit records in memory.
`publish` evaluates each complete season cohort through one immutable snapshot of the selected
formula, then writes the five version 1 reference-profile CSVs, deterministic audit and integrity
metadata, and a version 1 package manifest. Season context and all traditional, per-100, rate, and
advanced observations are columns in `player_stats.csv`; the reference profile does not publish an
explicit possession total. The manifest records the formula
version and exact document hash. Ineligible player-seasons and historical seasons
outside the formula's declared schedule retain their keys with empty calculated attributes.
Publication defaults to the ignored
`reference_data/packages/reference-v1` directory and stages and validates the complete package
before replacing an existing destination atomically.

The application may import `player_data_contracts` and `player_attribute_engine`. It must never
import `roster_generator`.
