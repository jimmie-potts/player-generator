# Current roster output

This directory contains version 1 game-facing sample output: a combined league roster JSON and a
flat player CSV used for inspection and tests.

No source player ID, source player name, or direct reference-row identifier is written here. Use the
comparison report under `reports/` to assess distribution accuracy without linking roster players to
individual reference players.

Version 2 will replace this directory and the combined output contract with a normalized,
player-only package under `roster_data/`. See the
[roster-package epic](../docs/planning/epics/EPIC-04-roster-package.md). That output does not exist
yet.
