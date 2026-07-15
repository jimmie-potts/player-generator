# EPIC-08: NBA-GM MVP roster handoff

- **Status:** ready
- **Outcome:** Freeze and publish a deterministic player-only MVP package that NBA-GM can validate
  and consume directly, with one consolidated statistics table and a synthetic conformance fixture.
- **Dependencies:** EPIC-04

## Why

NBA-GM will use the roster generator's currently available traditional, rate, possession, and
advanced statistics as inputs to its MVP simulation model. The producer and consumer need one
language-neutral contract and fixture before their implementations can proceed independently.

## Stories

- [US-016: Define the NBA-GM MVP roster contract](../user-stories/US-016-nba-gm-mvp-roster-contract.md)
- [US-017: Publish the consolidated MVP roster package](../user-stories/US-017-publish-consolidated-mvp-roster.md)
- [US-018: Generate a roster review workbook](../user-stories/US-018-roster-review-workbook.md)

US-016 and US-017 are required for the MVP handoff. US-018 is an optional, non-blocking human-review
follow-up and is not required to complete the machine-to-machine integration.

## Success criteria

- The canonical handoff contains exactly `manifest.json`, `players.csv`, `player_stats.csv`, and
  `player_attributes.csv`.
- NBA-GM can implement its consumer independently from a machine-readable contract and fully
  synthetic conformance fixture.
- `season` is an integer season-ending year; `2025` identifies the 2024-25 season.
- Every currently published roster statistic remains available as an MVP simulation input.
- Statistical identities, formula provenance, determinism, atomic publication, and the
  reference-to-roster identity boundary remain intact.
- The reference package retains its separate season, traditional-stat, and advanced-stat tables.

## Non-goals

- ESPN-derived simulation statistics, deeper tracking or play-type metrics, personality traits or
  descriptions, or any other post-MVP enrichment.
- Teams, player-team assignment, coaches, contracts, schedules, or NBA-GM league context.
- NBA-GM-specific rating, tendency, or simulation transformations.
- XLSX as a canonical integration format.
- A compatibility wrapper, dual publication, or migration path for a consumer that has not yet
  integrated the current roster contract.

## Risks

- Producer and consumer implementations can drift if they rely on prose instead of the same schema
  and fixture.
- A sampled statistical season can be mistaken for NBA-GM's fictional league season unless the
  distinction is explicit.
- Merging tables can obscure metric units or derivation rules unless the contract classifies every
  field.
- A human workbook can accidentally become authoritative unless it remains generated, values-only,
  and outside canonical package integrity coverage.
