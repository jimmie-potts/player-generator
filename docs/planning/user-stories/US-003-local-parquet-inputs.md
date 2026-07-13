# US-003: Register local Parquet inputs

- **Status:** in_progress
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

### 2026-07-13

- Began replacing the single-source pinned-download assumption with an adapter-versioned registry
  for caller-supplied local Parquet files.
- Kept the current download and wide build commands as explicitly legacy interfaces because the
  roster generator does not consume normalized reference packages until US-008.
- Selected an application-owned local registry that records resolved input paths and provenance
  metadata without copying or tracking the source files.
- Defined adapter schema version 1 for `nba_playerstats` using the implemented player-stat fields
  plus aggregate-team context, and for `espn_player_details` using the conservative required
  identity fields `id` and `displayName`.
- Derived unspecified source IDs from source type and a sanitized filename stem; explicit IDs remain
  available for a single input. Registrations validate the complete batch before an atomic registry
  replacement, preserve the first processing timestamp on identical re-registration, and report
  changed hashes or other source-ID conflicts.
- Persisted license status as `unknown` when the caller cannot supply a reviewed status. Upstream
  version remains optional and is recorded when known.
- Focused validation: `.venv/bin/python -m pytest apps/reference-data/tests/test_registration.py -q`
  passed 11 tests; targeted Ruff checks for the registration, adapter, CLI, and test modules passed.

## Completion notes

Pending. Record supported source schema versions, fixture coverage, commands, and source-specific
learnings before changing status to `complete`.
