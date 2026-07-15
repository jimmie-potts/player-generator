# EPIC-06: Formula workbench

- **Status:** complete
- **Outcome:** Make formulas explainable and show immediate player-level effects of temporary edits.
- **Dependencies:** EPIC-05

## Stories

- [US-011: Inspect formulas and calculations](../user-stories/US-011-inspect-formulas.md)
- [US-012: Preview formula adjustments](../user-stories/US-012-preview-adjustments.md)
- [US-013: Compare representative players](../user-stories/US-013-compare-players.md)

## Success criteria

- A React/TypeScript client displays components, raw metrics, percentiles, contributions, and output.
- Weight, direction, and anchor edits update previews without changing active configuration.
- Tier-stratified representatives are shown by default, with mutually exclusive baseline Top 25 and
  session-only custom-list views for alternate comparison strategies.
- Changed authoritative preview values are visually conspicuous throughout the persistent summary,
  formula-derived breakdown, and comparison output: green indicates an increased outcome or
  movement toward rank 1, red indicates a decrease or movement away, blue identifies changed weight
  allocation without judging it as a gain or loss, and signed text and arrows make direction
  understandable without color.
- Reset and export make experimentation reversible and portable.

## Non-goals

- Editing arbitrary expressions.
- Saving presets or modifying repository configuration.
- Duplicating formula logic in TypeScript.

## Risks

- Fast UI feedback can mask stale or failed API calculations if request state is not explicit.
- Ranking deltas need stable baseline and preview cohorts to be meaningful.

## Implementation notes

- **2026-07-14:** Started after EPIC-05 and US-010 were merged and verified complete. The approved
  designer workflow tunes existing component weights, directions, and rating anchors only. Its
  default comparison uses three representatives from each populated talent tier, reserves room for
  ten session-only pins within the 25-player preview bound, and exports the exact server-validated
  formula document with a designer-supplied formula version.
- **2026-07-14 refinement:** Reworked the editing surface around a persistent desktop comparison:
  the formula and authoritative-explanation panes share one viewport-bounded height, the formula
  scrolls independently, and the rating summary remains visible while its detailed trace is
  expandable. Narrow layouts return both panes to normal document flow. Native percentage sliders,
  a stacked allocation summary, section-level expandable guidance, and a glossary improve the
  designer workflow without moving validation or evaluation out of the preview API, as recorded in
  [D-028](../DECISIONS.md#d-028-accessible-exact-allocation-editing-and-persistent-explanation).
- **2026-07-14 comparison-view refinement:** Reopened US-013 to replace the combined tier sample and
  pin model with three mutually exclusive views: the default tier sample, a fixed baseline-overall
  Top 25, and a session-only custom list of up to 25 searched players. Each view submits only its own
  IDs for detailed preview results; the authoritative API still evaluates the complete fixed cohort
  for every rating, percentile, and rank. The superseding composition is recorded in
  [D-029](../DECISIONS.md#d-029-mutually-exclusive-comparison-sets-over-one-fixed-cohort).
- **2026-07-14 preview-impact refinement:** Strengthened the visual feedback loop without changing
  formula authority or calculation semantics. Nonzero changes in the persistent scoreboard,
  formula-derived component preview cells, and comparison rating and rank cells use green for
  outcome increases or movement toward rank 1 and red for decreases or movement away. Changed
  normalized weights use blue because allocation alone is not a positive or negative outcome. All
  cues are backed by signed values, directional arrows, and accessible labels; unchanged and
  non-result states remain neutral and explicitly identified.
- **2026-07-14 PR review follow-up:** Addressed three comparison usability gaps: new custom searches and
  removals clear stale add errors, an active failed Top 25 view presents an explicit retry action,
  and player-selection controls announce a separated display name and human-readable tier. These
  changes preserve the same session-only state and server-authoritative calculations.

## Completion notes

- **Initial completion:** 2026-07-14 in
  [PR #11](https://github.com/jimmie-potts/player-generator/pull/11), beginning with implementation
  commit `6849209`.
- **Initial outcome:** The local React workbench explains every active player attribute, previews only
  approved session edits through the shared Python evaluator, compares deterministic players across
  the full talent curve, and exports the exact validated proposal JSON. It never calculates ratings
  or persists active configuration in the browser. D-029 later added separate Top 25 and custom-list
  views without changing those authority boundaries.
- **Initial validation:** All 376 Python tests, 35 frontend tests, Ruff, the production TypeScript/Vite
  build, integrity manifest, and diff checks pass. A clean `npm ci` also verifies the Node 22.12 CI
  dependency layout. The real Vite proxy and preview API were exercised against the ignored
  582-player 2026 package; its 15-player adjusted preview completed in 191 ms.
- **First UI refinement validation:** The expanded frontend suite passed all 50 tests,
  including exact-allocation rebalancing, accessible sliders, singleton attributes, collapsible
  explanations, glossary content, and preservation of edits and comparison state across workbench
  navigation.
- **Final refinement completion:** 2026-07-14 in
  [PR #11](https://github.com/jimmie-potts/player-generator/pull/11).
- **Final outcome:** The workbench now offers mutually exclusive Tier sample, fixed baseline-overall
  Top 25, and session-only Custom list views while the API and shared Python engine retain the
  complete fixed cohort for ratings, percentiles, ranks, and explanations. The refined editor adds
  normalized accessible sliders, deterministic exact allocation after an edit, a persistent desktop
  rating summary with expandable details, generous section guidance, responsive normal flow, and a
  formula- and metric-aware glossary. No browser rating evaluator, persistence, or deployment path
  was introduced.
- **Final validation:** `npm run workbench:test` passed 73 tests;
  `npm run workbench:build`, `.venv/bin/python -m ruff check .`, and `git diff --check` passed. The
  maximum-cohort Top 25 preview test
  `apps/formula-workbench/api/tests/test_startup_and_performance.py::test_maximum_cohort_top_25_preview_meets_the_3000ms_budget`
  completed locally in 1.63 seconds under the unchanged 3,000 ms budget. The pre-regeneration Python
  run reached 375 passed with only the expected manifest-hash mismatch; refreshing
  `FILE_MANIFEST.sha256` and rerunning the suite passed all 376 tests.
- **Preview-impact refinement validation:** `npm run workbench:test` passed 77 tests;
  `npm run workbench:build`, `.venv/bin/python -m pytest` (376 passed),
  `.venv/bin/python -m ruff check .`, `sha256sum -c FILE_MANIFEST.sha256`, and staged diff checks
  passed after adding visible, non-color-only impact feedback and a completed-preview announcement.
- **PR review follow-up outcome:** Comparison failures now provide an in-place recovery path and no
  longer mask fresh custom-list searches or let late add completions erase newer results, while
  player-selection names expose readable tier context to assistive technology. Focused regression
  coverage protects these behaviors.
- **PR review follow-up validation:** `npm run workbench:test` passed 85 tests;
  `npm run workbench:build`, `.venv/bin/python -m pytest` (376 passed),
  `.venv/bin/python -m ruff check .`, `sha256sum -c FILE_MANIFEST.sha256`, and staged diff checks
  passed.
- **Deviations and follow-ups:** No unrecorded deviations were introduced beyond D-028 and D-029.
  Saved comparison groups, collaborative sharing, authentication, persistence, approval, and
  deployment remain out of scope; custom players remain page-session state.
- **Decisions and learnings:** [D-026](../DECISIONS.md#d-026-server-authoritative-designer-proposals-and-tiered-comparison),
  [D-027](../DECISIONS.md#d-027-session-scoped-client-state-with-cancellable-authoritative-previews),
  [D-028](../DECISIONS.md#d-028-accessible-exact-allocation-editing-and-persistent-explanation),
  and [D-029](../DECISIONS.md#d-029-mutually-exclusive-comparison-sets-over-one-fixed-cohort)
  define the server-authoritative, session-only workflow, refined authoring surface, and active
  comparison-set model.
  Reusable findings are recorded for
  [US-011](../LEARNINGS.md#2026-07-14--us-011),
  [US-012](../LEARNINGS.md#2026-07-14--us-012), and
  [US-013](../LEARNINGS.md#2026-07-14--us-013).
- **Remaining roadmap:** EPIC-07's future player-adjacent contract definitions remain unstarted.
  Authentication, persistence, approval, deployment, arbitrary formulas, and generated team or
  coach data are not part of this epic.
