# EPIC-08: NBA-GM player data contract version 1

- **Status:** in_progress
- **Outcome:** Freeze and publish the baseline version 1 reference and roster profiles, with one
  consolidated statistics table and a deterministic player-only roster fixture that NBA-GM can
  validate independently.
- **Dependencies:** EPIC-04

## Why

NBA-GM will use the roster profile's traditional, rate, possession, and advanced observations as
inputs to its MVP simulation model. Version 1 gives producer and consumer one language-neutral
baseline and fixture so their implementations can proceed independently. Player-generator also
derives the corresponding reference files from the same shared definitions so its calibration and
generated outputs do not drift.

## Stories

- [US-016: Freeze player data contract version 1](../user-stories/US-016-nba-gm-mvp-roster-contract.md)
- [US-017: Publish player data contract version 1](../user-stories/US-017-publish-consolidated-mvp-roster.md)
- [US-018: Generate a roster review workbook](../user-stories/US-018-roster-review-workbook.md)

US-016 and US-017 are required for the MVP handoff. US-018 is an optional, non-blocking human-review
follow-up and is not required to complete the machine-to-machine integration.

## Success criteria

- The canonical handoff contains exactly `manifest.json`, `players.csv`, `player_stats.csv`, and
  `player_attributes.csv`.
- The corresponding reference and roster player files derive their shared fields and CSV formatting
  from one contract definition, with explicit and tested profile-only extensions.
- Both version 1 profiles publish traditional and advanced metrics in `player_stats.csv`.
- NBA-GM can implement its consumer independently from a machine-readable contract and fully
  synthetic conformance fixture.
- `season` is an integer season-ending year; `2025` identifies the 2024-25 season.
- Every governed version 1 roster statistic is available as an MVP simulation input.
- Statistical identities, formula provenance, determinism, atomic publication, and the
  reference-to-roster identity boundary remain intact.
- Reference-only season-context columns, source identities, provenance, and audit data remain absent
  from the NBA-GM roster handoff.

## Non-goals

- ESPN-derived simulation statistics, deeper tracking or play-type metrics, personality traits or
  descriptions, or any other post-MVP enrichment.
- Teams, player-team assignment, coaches, contracts, schedules, or NBA-GM league context.
- NBA-GM-specific rating, tendency, or simulation transformations.
- XLSX as a canonical integration format.

## Risks

- Producer and consumer implementations can drift if they rely on prose instead of the same schema
  and fixture.
- Reference and roster files can drift if common fields are copied into separate schema definitions
  instead of deriving from a shared definition with a parity test.
- A sampled statistical season can be mistaken for NBA-GM's fictional league season unless the
  distinction is explicit.
- Merging tables can obscure metric units or derivation rules unless the contract classifies every
  field.
- A human workbook can accidentally become authoritative unless it remains generated, values-only,
  and outside canonical package integrity coverage.
