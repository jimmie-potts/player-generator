# US-013: Compare representative players

- **Status:** complete
- **Epic:** [EPIC-06](../epics/EPIC-06-workbench.md)
- **Dependencies:** US-012

## User story

As a designer, I want to compare formula effects across representative players so that tuning is not
based on one example.

## Acceptance criteria

- Provide mutually exclusive `Tier sample`, `Top 25`, and `Custom list` comparison views, with the
  tier sample selected by default.
- Show one to three highest-ranked eligible players from each populated talent tier, with three per
  tier by default.
- Show a fixed Top 25 selected and ordered by baseline overall rank so temporary edits do not
  reshuffle its membership.
- Search by partial display name and stable reference `playerId`, then add or remove up to 25 unique
  players in the custom list.
- Send only the active view's player IDs for detailed preview results and preserve each view's
  selected player while switching when it remains available.
- Never submit more than the preview API's 25-player detail bound; block an oversized tier sample
  with guidance to reduce the per-tier count or choose another view.
- Show baseline rating, preview rating, absolute delta, baseline rank, preview rank, and rank movement
  for the selected attribute and overall when affected.
- Highlight the players with the largest positive and negative changes.
- Keep baseline and preview cohorts fixed for a preview so rank changes are comparable.
- Preserve the custom list for the browser page session only.
- Clearly distinguish no change, missing input, excluded player, and recalculation failure.

## Out of scope

- Saved comparison groups or collaborative sharing.

## Validation

- Tests cover all three view memberships, mode switching, search normalization, custom-list bounds
  and removal, largest-change signals, tied ranks, missing players, and session reset.

## Implementation notes

- **2026-07-14:** Began after the US-012 adjustment and stale-response tests passed. The user-approved
  recommendation replaced one top-overall sample with a tier-stratified default, recorded in
  [D-026](../DECISIONS.md#d-026-server-authoritative-designer-proposals-and-tiered-comparison).
- **2026-07-14:** Kept representative selection deterministic and separate from session pins. The API
  calculates selected-attribute and overall ranks over the complete fixed cohort; the browser only
  groups and highlights the bounded response.
- **2026-07-14 review follow-up:** Cleared prior search hits as soon as a different non-empty query
  begins its debounce, and made both pin success and failure paths reject results from an earlier
  session generation.
- **2026-07-14 refinement:** Kept the selected player's authoritative rating summary visible beside
  the independently scrolling formula pane on desktop so weight changes can be evaluated without
  losing the result. The comparison controls and table retain normal page flow and remain API-owned
  views over the fixed cohort; the responsive layout removes sticky behavior when the panes stack.
  This responsive comparison layout is recorded in
  [D-028](../DECISIONS.md#d-028-accessible-exact-allocation-editing-and-persistent-explanation).
- **2026-07-14 comparison-view refinement:** Reopened the story after the designer requested separate
  views for the tier sample, the baseline-overall Top 25, and a custom list of up to 25 players. The
  views are mutually exclusive: only the active list supplies `selectedPlayerIds`, while all
  calculations and ranks continue to use the complete fixed cohort. Top 25 membership and ordering
  remain fixed to the baseline response, and the custom list remains session-only. This refinement
  explicitly supersedes the earlier tier-plus-pins composition in
  [D-029](../DECISIONS.md#d-029-mutually-exclusive-comparison-sets-over-one-fixed-cohort).

## Completion notes

- **Initial completion:** 2026-07-14 in
  [PR #11](https://github.com/jimmie-potts/player-generator/pull/11), beginning with implementation
  commit `6849209`.
- **Initial delivery:** Added a deterministic representative endpoint and a comparison table grouped from
  highest to lowest talent tier. The default is three players from each of the five populated tiers
  in the local 2026 package (15 total), configurable from one through three per tier. Normalized
  partial-name and stable-`playerId` search can add and remove up to ten independent session pins
  without replacing the tier sample.
- **Comparison semantics:** Each row shows baseline and preview values, absolute delta, and baseline,
  preview, and movement ranks for the selected attribute and overall. The API uses minimum-rank tie
  semantics over the same complete baseline/preview cohort. The client highlights every tied largest
  positive or negative attribute change and distinguishes no change, missing input, exclusion, and
  preview failure.
- **Initial approved deviation:** The original top-overall-only default would overrepresent elite players.
  The revised acceptance criterion and
  [D-026](../DECISIONS.md#d-026-server-authoritative-designer-proposals-and-tiered-comparison)
  adopt three highest-ranked eligible players per populated tier while reserving ten of the API's
  25 selected-player slots for pins. The table preserves deterministic tier/rank order and uses
  largest-change signals instead of resorting rows after each edit. D-029 later supersedes the
  combined tier-plus-pins composition while retaining the tier sample as the default view.
- **Initial validation:** `.venv/bin/python -m pytest` passed 376 tests;
  `.venv/bin/python -m ruff check .`, `npm run workbench:build`, and `git diff --check` passed;
  `npm run workbench:test` passed 35 tests. API tests cover tier ordering, complete-cohort selected-
  attribute ranks and tied ranks; integration tests cover all five default groups, search, pin and
  unpin, retained defaults, largest gain/loss signals, and failure clearing. A live smoke test
  returned baseline ranks `1/2/3`, `12/12/12`, `33/33/33`, `85/85/85`, and `183/183/183` across the
  five groups.
- **First UI refinement validation:** `npm run workbench:test` passed 50 tests, including
  preservation of a weight edit and session pin while navigating to the glossary and back; the
  production workbench build and diff checks also pass.
- **Final refinement completion:** 2026-07-14 in
  [PR #11](https://github.com/jimmie-potts/player-generator/pull/11).
- **Final refinement delivery:** Replaced the combined representative-and-pin table with mutually
  exclusive Tier sample, fixed baseline-overall Top 25, and session-only Custom list views. The tier
  sample remains the default, Top 25 retains its baseline membership and order during temporary
  edits, and search can build a unique custom list of up to 25 players. Switching modes preserves
  their independent state and sends only the active list for detailed preview results.
- **Workbench refinement:** Added normalized percentage sliders with deterministic exact allocation
  after an edit, while presenting untouched positive-sum source weights as normalized shares. The
  selected-player summary remains visible beside the independently scrolling Formula pane on
  desktop, calculation details and generous section guidance are expandable, pending previews retain
  the prior summary, narrow screens return to normal flow, and the Glossary combines stable terms
  with formula- and metric-derived entries.
- **Authority:** Every view remains a bounded selection over the same complete fixed season cohort.
  The preview API and shared Python engine, not the React client, calculate ratings, percentiles,
  selected-attribute ranks, overall ranks, contributions, and explanation details.
- **Deviations:** No unrecorded deviations. The authoring and responsive-layout refinements follow
  [D-028](../DECISIONS.md#d-028-accessible-exact-allocation-editing-and-persistent-explanation), and
  [D-029](../DECISIONS.md#d-029-mutually-exclusive-comparison-sets-over-one-fixed-cohort) explicitly
  supersedes the earlier comparison composition while preserving its authority boundaries.
- **Final validation:** `npm run workbench:test` passed 73 tests;
  `npm run workbench:build`, `.venv/bin/python -m ruff check .`, and `git diff --check` passed. The
  focused
  `.venv/bin/python -m pytest apps/formula-workbench/api/tests/test_startup_and_performance.py::test_maximum_cohort_top_25_preview_meets_the_3000ms_budget`
  command passed locally in 1.63 seconds under the unchanged 3,000 ms budget. Before regenerating
  the required repository manifest,
  `.venv/bin/python -m pytest` reached 375 passed with only the expected manifest-hash mismatch; the
  synchronized manifest and final rerun passed all 376 tests.
- **Follow-ups:** Saved comparison groups and collaborative sharing remain deliberately out of
  scope. The custom list disappears with the browser page session.
- **Learnings:** Tier stratification reveals sensitivity across the rating curve without changing
  percentile populations; search results and custom-list errors must also be isolated to the query
  and session that produced them. Ranks remain server-owned and cohort-wide rather than depend on
  the displayed sample, and comparison modes must not combine their selected IDs. These findings
  are recorded in
  [LEARNINGS.md](../LEARNINGS.md#2026-07-14--us-013).
