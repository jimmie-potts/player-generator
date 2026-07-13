# Reference-data application

This Python application owns the current local source download, Parquet ingestion, canonical
player-season projection, reference rating calculation, and processed reference outputs.

```bash
reference-data --help
reference-data download
reference-data build
```

Its configuration boundary is `config/default.yaml` within this application. Raw and processed
named data remain local and untracked. The remote download and wide CSV outputs are transitional
version 1 behavior; local multi-source registration and normalized reference packages are planned
in EPIC-02.

The application may import `player_data_contracts` and `player_attribute_engine`. It must never
import `roster_generator`.
