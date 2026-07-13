# Version 2 learning log

This is an append-oriented record of reusable facts discovered while planning or implementing the
redesign. Each completed story must add any relevant findings here and retain detailed evidence in
its completion notes.

## Planning baseline — 2026-07-12

- The current implementation is a single Python package in which ingestion, formulas, roster
  generation, comparison, and CLI orchestration directly import one another.
- Current rating formulas are Python dictionaries in `ratings.py`; weights and inputs cannot be
  edited safely by a browser without first extracting a declarative contract.
- The current source manifest downloads one pinned `playerstats.parquet` URL. Version 2 local-file
  ingestion is a behavior change, not just a new command name.
- The current processed model uses wide player-season and latest-season CSVs. Moving to normalized
  contracts requires explicit keys, join validation, and provenance tables.
- The current generator emits a combined roster JSON and a flattened player CSV. Version 2 instead
  publishes a player-only package split by concern.
- Current team definitions and assignments exist, but first-release version 2 team output is
  deliberately out of scope.
- The upstream `llimllib/nba_data` snapshot has no observed root license. Raw and transformed named
  reference data should remain local and untracked unless redistribution rights are established.
- ESPN play-style data can improve future attributes, but source-ID reconciliation and schema
  differences make it a separate adapter and formula-extension story.

## Entry format

Add new entries under a dated heading and identify the story that produced the learning:

```text
### YYYY-MM-DD — US-NNN

- What was learned.
- Why it matters to later stories.
- Any constraint or validation that should be reused.
```
