# EPIC-02: Reference-data builder

- **Status:** in_progress
- **Outcome:** Transform local Parquet inputs from multiple sources into a validated canonical CSV
  package.
- **Dependencies:** EPIC-01

## Why

Downstream generation and analysis need a stable interface that is independent of upstream column
names, source availability, and schema changes.

## Stories

- [US-003: Register local Parquet inputs](../user-stories/US-003-local-parquet-inputs.md)
- [US-004: Normalize sources into a canonical model](../user-stories/US-004-canonical-normalization.md)
- [US-005: Publish normalized reference CSVs](../user-stories/US-005-reference-csv-package.md)

## Success criteria

- Local NBA and ESPN Parquet files can be validated through source-specific adapters.
- Player identity reconciliation, source precedence, and unmatched records are explicit and auditable.
- The published package contains versioned relational CSVs and provenance.
- Identical input files and configuration produce identical data rows.

## Non-goals

- Automated remote downloads.
- Shipping raw or transformed named reference data with the repository.
- Roster generation or attribute mutation.

## Risks

- Traded-player and aggregate rows can create ambiguous player-season grain.
- Cross-source player matching can create silent identity corruption if ambiguity is not reported.
- Upstream license status limits redistribution even when transformation is technically successful.
