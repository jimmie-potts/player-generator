# US-015: Publish reference player attributes

- **Status:** in_progress
- **Epic:** [EPIC-03](../epics/EPIC-03-attributes.md)
- **Dependencies:** US-005, US-007, US-008

## User story

As a data consumer, I want calculated attributes in the published reference package so that
reference player-seasons can be inspected without running a separate formula-evaluation step.

## Acceptance criteria

- Publish `player_attributes.csv` in reference package version 2 with one row for every published
  player-season.
- Evaluate each season as a complete percentile cohort through the shared attribute engine and the
  selected declarative formula document.
- Preserve `playerSeasonId`, `playerId`, and `season` for every row; unsupported or ineligible
  attributes remain empty rather than receiving fabricated values.
- Govern the new CSV's ordered headers, scalar types, nullability, bounds, keys, and relationships
  through reference contract version 2.
- Record the formula version and exact formula-document hash in the package manifest and include
  the attributes file in package integrity metadata.
- Identical normalized inputs and formula bytes produce identical attribute rows and content hashes.
- Continue to read reference package version 1 while making version 2 the publication default.
- Roster generation continues to evaluate its requested formula rather than copying published
  reference ratings into generated roster output.

## Out of scope

- Publishing per-component calculation explanations.
- Changing formula version `1.0.0`, its weights, eligibility, anchors, ratings, or talent tiers.
- Adding unsupported attributes or changing roster package contracts.

## Validation

- Contract tests cover ordered headers, nullable ratings, bounds, unique keys, foreign keys, and
  exact player-season key sets.
- Publication tests cover multiple season cohorts, evaluator parity, empty ineligible ratings,
  formula provenance, determinism, and atomic failure cleanup.
- Consumer tests cover valid version 1 and version 2 packages, integrity failures, unsupported
  versions, and unchanged roster-generation behavior.

## Implementation notes

### 2026-07-13

- Started after US-005, US-007, and US-008 completed. Reference contract version 2 is additive:
  the six version 1 inputs retain their columns and a seventh season-grain attribute table is added.
- Formula version `1.0.0` continues to declare reference input contract version 1 because its input
  vocabulary and calibration are unchanged. A version 2 package satisfies that input requirement.
- The normalized source contains seasons outside formula version `1.0.0`'s declared schedule.
  Those player-season keys remain in `player_attributes.csv` with empty calculated values and the
  formula version, rather than silently extending the approved calibration schedule.
- Detailed evaluator explanations remain available to later API work but are not published in the
  batch package.

## Completion notes

Pending implementation and validation.
