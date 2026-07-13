# US-009: Generate the normalized roster package

- **Status:** complete
- **Epic:** [EPIC-04](../epics/EPIC-04-roster-package.md)
- **Dependencies:** US-008

## User story

As a game developer, I want a normalized player-only CSV package so that bio, statistics, advanced
statistics, and attributes can be loaded independently.

## Acceptance criteria

- Publish `players.csv`, `player_stats.csv`, `player_advanced_stats.csv`,
  `player_attributes.csv`, and `manifest.json` as described in
  [DATA_CONTRACTS.md](../DATA_CONTRACTS.md).
- Generate player identities independently and use a stable roster `playerId` across every file.
- Produce traditional and advanced statistics by controlled mutation of a sampled reference
  player-season.
- Preserve valid relationships among minutes, totals, per-game, per-36, per-100, attempts, makes,
  percentages, and advanced fields after mutation.
- Omit fields lacking source inputs or approved generation rules.
- Exclude upstream names, player IDs, team IDs, source-row indexes, and any source-to-roster
  crosswalk.
- Write output atomically after all contract and relationship validation passes.
- The manifest records package version, reference-package hash, formula version, seed, configuration
  hash, row counts, and content hashes.
- Identical inputs produce identical data rows and hashes.

## Out of scope

- Team assignment, coach generation, contracts, health, personality, and unsupported tendencies.

## Validation

- Golden package and determinism tests.
- Statistical consistency properties and scale-bound checks.
- Identity-leak scans against reference IDs and names.
- Failure tests verify no partial package is published.

## Implementation notes

- **2026-07-13:** US-008 is complete. Roster contract version 1 will carry season, games, minutes,
  and one inferred possession basis in `player_stats.csv` because the player-only package has no
  separate season table. Generation mutates shooting attempts/accuracy and event totals, derives
  every dependent total/rate/percentage, then calculates attributes through the shared evaluator.
  The package is validated and identity-scanned in a same-parent staging directory before atomic
  replacement.

## Completion notes

- **Completed:** 2026-07-13
- **Pull request:** [PR #7](https://github.com/jimmie-potts/player-generator/pull/7)
- **Delivered:** Roster contract version 1 governs ordered and typed `players.csv`,
  `player_stats.csv`, `player_advanced_stats.csv`, and `player_attributes.csv` plus their unique
  keys, exact key sets, relationships, bounds, null rules, and statistical identities. Generation
  creates independent hashed IDs and Faker names, applies bounded mutation to attempts, shooting
  accuracy, event totals, bio values, and available advanced inputs, derives all dependent fields,
  evaluates attributes with formula version `1.0.0`, scans canonical and upstream identifiers for
  reference identity leakage, and atomically publishes the exact deterministic five-file package.
  Formula evaluation and its manifest hash use one immutable byte snapshot.
- **Mutation and consistency rules:** Makes never exceed attempts; field-goal totals decompose into
  two- and three-point values; points and rebounds are exact sums; percentages and per-game,
  per-36, and per-100 values are recomputed to eight decimals. D-018 supplies one published
  possession basis. Net ratings, eFG, true shooting, assist-to-turnover ratio, assist ratio,
  estimated turnover percentage, and defensive win shares per 36 are recomputed from published
  operands. Effective field-goal and true-shooting rates permit valid values through `1.5`.
  Assist-to-turnover uses `assists / max(turnovers, 1)` under D-021; assist ratio and estimated
  turnover percentage use the shared play-ending denominator in D-019. Rebound percentage remains
  an independently mapped and bounded source metric.
  Validation uses relative tolerance `1e-8` and absolute tolerance `1e-7` for serialized derived
  values.
- **Deviations:** Under D-003's clean version 2 break, the former combined league/team JSON, team
  assignment, flattened player CSV, and comparison command/report were retired rather than wrapped.
  Packages now live under ignored `roster_data/packages/roster-v1/` so generated output cannot mix
  with stale tracked examples.
- **Validation:** `.venv/bin/python -m pytest` passed 276 tests, including a fixed
  generator-to-publication golden package, deterministic bytes, valid zero-attempt shooters,
  identity leaks, manifest tampering, statistical invariants, and atomic rollback;
  `.venv/bin/python -m ruff check .`, `npm run workbench:test`, `npm run workbench:build`,
  `sha256sum -c FILE_MANIFEST.sha256`, and `git diff --check` passed.
- **Follow-up:** Teams, coaches, contracts, health, personality, tendencies, the preview API, and
  workbench behavior remain out of scope.
- **Learning:** Mutating a few primitive totals and deriving every dependent value produces a
  smaller, auditable generation surface than independently perturbing rates or ratings.
- **Review follow-up:** Contract and semantic regressions cover shooting efficiencies above `1.0`,
  and zero-turnover generated lines retain finite assist-to-turnover values and complete
  attributes. The focused generator/contract/publication suites passed 60 tests; the full Python
  suite passed 308 tests.
