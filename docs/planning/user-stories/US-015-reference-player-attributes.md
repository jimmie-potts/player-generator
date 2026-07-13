# US-015: Publish reference player attributes

- **Status:** complete
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

- **Completed:** 2026-07-13.
- **Pull request:** [#8](https://github.com/jimmie-potts/player-generator/pull/8), opened ready
  for review as a stacked PR against the still-open EPIC-04 branch.
- **Branch and implementation commit:** `agent/reference-attributes-v2`; `28655ea`.
- **Delivered:** additive `reference-v2.schema.json`; season-grain `player_attributes.csv`;
  per-season shared-engine evaluation; `publish --formula`; exact formula version/hash provenance;
  deterministic file and package hashes; and atomic version 2 publication.
- **Compatibility:** reference contract and package version 1 remain readable. Formula version
  `1.0.0` still requires the unchanged version 1 input vocabulary. The roster consumer validates
  v2 attributes but recalculates its requested formula, preserving custom proposals and the
  reference-to-roster identity boundary.
- **Historical seasons:** all 6,908 player-season keys from 2014 through 2026 are published.
  Seasons outside the formula's 2021–2026 schedule retain empty calculated values; supported but
  ineligible player-seasons follow the same empty-value contract without hiding other evaluator
  failures.
- **Local package sample:** the ignored registered NBA source produced 6,908 attribute rows, 2,212
  complete ratings, formula document hash
  `daee5cf36630bab1b50ce9030f57e1e35e17234266d894c3883141d7ee4f200f`, and package content
  hash `587ded9dc174bce4341da5c73cfe92587bb0401d02706d83705d4ed2ed38862d`.
  A second publication produced byte-identical data files and the same content hash.
- **Validation:** `.venv/bin/python -m pytest` (`300 passed`),
  `.venv/bin/python -m ruff check .`, `npm run workbench:test`, `npm run workbench:build`,
  `git diff --check`, and `sha256sum -c FILE_MANIFEST.sha256` passed. Real
  `reference-data publish` and `roster-generator generate` commands completed against the local
  version 2 package.
- **Follow-ups:** explanation publication remains out of scope; US-010 may expose the evaluator's
  existing explanation model through the preview API. PR #8 should be retargeted to `main` after
  PR #7 merges.
- **Learnings:** exact-file-set packages require explicit additive versions; evaluator identity
  ordering must be checked before attaching season keys; formula schedule gaps should yield
  explicit empty outputs rather than invented policy; and published reference provenance does not
  replace consumer-selected formula evaluation. These findings are recorded in
  [LEARNINGS.md](../LEARNINGS.md#2026-07-13--us-015).
