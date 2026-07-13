# Roster-generator application

This Python application owns the current template sampling, player and team generation, roster
serialization, and population comparison reports.

```bash
roster-generator --help
roster-generator generate
roster-generator compare
```

Its configuration boundary is `config/default.yaml` within this application. The current generator
reads the processed player-season CSV published by the reference-data application and never imports
its source adapters or pipeline. A versioned normalized reference package and player-only roster
package are planned in later stories.

The application may import shared data-contract code. It must never import `reference_data_app`.
