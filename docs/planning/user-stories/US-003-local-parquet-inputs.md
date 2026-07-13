# US-003: Register local Parquet inputs

- **Status:** ready
- **Epic:** [EPIC-02](../epics/EPIC-02-reference-data.md)
- **Dependencies:** US-001

## User story

As a data maintainer, I want to register local Parquet files so that reference packages can be built
without remote downloads or redistribution.

## Acceptance criteria

- A reference-data CLI command accepts one or more local paths and an explicit source type.
- Initial registered source types are `nba_playerstats` and `espn_player_details`.
- Registration validates file existence, Parquet readability, required columns, and supported
  adapter schema version before transformation.
- Each input records a source ID, source type, original filename, SHA-256 hash, adapter version,
  source row count, and processing timestamp.
- Re-registering an identical file is idempotent; conflicting source IDs or changed content are
  reported.
- Inputs remain outside tracked outputs and are never copied into the repository.
- Errors name the file, adapter, and missing or incompatible fields.

## Out of scope

- Browser uploads, API uploads, remote downloads, or automated source refresh.

## Validation

- Adapter fixtures cover valid input, missing columns, invalid Parquet, changed hash, duplicate
  registration, and unsupported schema versions.
- Provenance output is deterministic apart from explicitly non-deterministic processing metadata.

## Implementation notes

Append dated notes here while the story is active.

## Completion notes

Pending. Record supported source schema versions, fixture coverage, commands, and source-specific
learnings before changing status to `complete`.
