# US-008: Consume a published reference package

- **Status:** complete
- **Epic:** [EPIC-04](../epics/EPIC-04-roster-package.md)
- **Dependencies:** US-005, US-007

## User story

As a game developer, I want roster generation to consume a published reference package so that it
does not depend on raw sources or adapter internals.

## Acceptance criteria

- The roster-generator CLI accepts a reference-package directory and roster configuration.
- It validates the package manifest, required files, content hash, contract versions, key
  relationships, and compatible formula version before sampling.
- It never imports source adapters or reads upstream Parquet files.
- Eligibility filters, season selection, recency weights, roster size, and random seed are explicit
  configuration.
- Validation failures identify the incompatible file, contract, or relationship before generation
  starts.
- Identical reference package, configuration, formula document, and seed select the same templates.

## Out of scope

- Building or repairing a reference package automatically.

## Validation

- Integration fixtures cover valid packages, missing files, hash mismatch, unsupported versions,
  orphan IDs, empty eligible populations, and deterministic template selection.

## Implementation notes

- **2026-07-13:** Confirmed US-005 and US-007 are complete. The implementation will keep package
  loading in `roster_generator`, validate the published manifest and normalized CSV relationships
  before template selection, and pass joined rows to the shared attribute engine without importing
  reference-data application code.

## Completion notes

- **Completed:** 2026-07-13
- **Pull request:** Pending EPIC-04 handoff; the ready pull-request link will be added before final
  publication is reported complete.
- **Delivered:** The roster CLI accepts config plus reference-package, formula, output, and seed
  overrides. `roster_generator.reference_package` verifies reference manifest/package version 1,
  all six CSV contract versions, exact required files, per-file hashes and row counts, the audit row
  count, aggregate content hash, normalized table relationships, and formula reference-contract
  and roster-output compatibility before returning a typed player-season join. Selection evaluates
  complete season cohorts before applying explicit season, recency, games, minutes, size,
  replacement, and seed controls.
- **Deviations:** None. The story remains a consumer only and never builds or repairs a reference
  package.
- **Validation:** `.venv/bin/python -m pytest
  apps/roster-generator/tests/test_reference_selection.py` passed 23 tests, including missing
  files, hash/row/version/relationship failures, formula output compatibility, empty populations,
  deterministic selection, and end-to-end CLI publication; focused Ruff passed.
- **Follow-up:** US-009 consumes the selected internal templates and must not serialize their
  reference identities or any crosswalk.
- **Learning:** Validate the full published package, then recheck its hashes after typed reads so a
  mutable package path cannot change between manifest validation and sampling.
