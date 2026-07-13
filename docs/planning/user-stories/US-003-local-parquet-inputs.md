# US-003: Register local Parquet inputs

- **Status:** complete
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
- PR review added reusable registered-source verification. Consumers can now compare the current
  local SHA-256 hash and adapter row count with stored provenance and fail with recovery guidance
  when a referenced file is missing or has changed.

## Completion notes

- **Completed:** 2026-07-13
- **Branch and implementation commit:** `agent/implement-us-003-us-005`; `ee0e13f`.
- **Delivered:** A `reference-data register` command for one or more caller-owned local Parquet
  files; version 1 adapters for `nba_playerstats` and `espn_player_details`; contextual schema and
  readability validation; and an ignored, atomically written provenance registry with stable source
  IDs, input paths, filenames, hashes, adapter versions, row counts, timestamps, upstream versions,
  and license status.
- **Compatibility boundary:** The existing `download` and wide `build` commands remain as explicit
  legacy interfaces until US-008 moves roster generation to the normalized reference package. No
  remote acquisition behavior was added to the version 2 registration path.
- **Validation:** `.venv/bin/python -m pytest apps/reference-data/tests/test_registration.py -q`
  passed 11 tests; `.venv/bin/python -m pytest apps/reference-data/tests tests/test_architecture.py
  tests/test_entrypoints.py -q` passed 24 tests; targeted Ruff and `git diff --check` passed; and a
  local ignored NBA file registered from its existing location without being copied.
- **Fixture coverage:** Both source types, multiple paths, deterministic registry ordering,
  idempotent re-registration, changed content, conflicting IDs, missing fields, invalid Parquet,
  unsupported adapter versions, all-or-nothing batch validation, CLI metadata, and default unknown
  license status.
- **Follow-up:** US-004 consumes the registry through these adapters, performs reconciliation, and
  creates canonical tables. US-005 publishes those tables; US-008 retires the legacy build seam.
- **Learning:** Parquet metadata does not supply the application adapter version, so callers select
  it explicitly. Preserving the original processing timestamp on identical registration keeps
  provenance stable across later deterministic package rebuilds.
