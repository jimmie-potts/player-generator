# Roster output

This directory contains the current game-facing sample output:

- `default_roster.json`: combined league roster JSON.
- `players.csv`: flat player table used for inspection and tests.

No source player ID, source player name, or direct reference-row identifier is written here. Use the
comparison report under `reports/` to assess distribution accuracy without linking roster players to
individual reference players.

The normalized player-only package described by
[EPIC-04](../docs/planning/epics/EPIC-04-roster-package.md) remains future work. Until then, these
files retain the current version 1 combined roster and flattened-player contracts under the neutral
roster path.
