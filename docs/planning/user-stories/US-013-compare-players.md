# US-013: Compare representative players

- **Status:** complete
- **Epic:** [EPIC-06](../epics/EPIC-06-workbench.md)
- **Dependencies:** US-012

## User story

As a designer, I want to compare formula effects across representative players so that tuning is not
based on one example.

## Acceptance criteria

- Show one to three highest-ranked eligible players from each populated talent tier, with three per
  tier by default.
- Search by partial display name and stable reference `playerId`.
- Pin and unpin any reference player without removing the default sample.
- Show baseline rating, preview rating, absolute delta, baseline rank, preview rank, and rank movement
  for the selected attribute and overall when affected.
- Highlight the players with the largest positive and negative changes.
- Keep baseline and preview cohorts fixed for a preview so rank changes are comparable.
- Preserve pinned players for the browser session only.
- Clearly distinguish no change, missing input, excluded player, and recalculation failure.

## Out of scope

- Saved comparison groups or collaborative sharing.

## Validation

- Tests cover default ranking, search normalization, pinning, largest-change signals, tied ranks,
  missing players, and session reset.

## Implementation notes

- **2026-07-14:** Began after the US-012 adjustment and stale-response tests passed. The user-approved
  recommendation replaced one top-overall sample with a tier-stratified default, recorded in
  [D-026](../DECISIONS.md#d-026-server-authoritative-designer-proposals-and-tiered-comparison).
- **2026-07-14:** Kept representative selection deterministic and separate from session pins. The API
  calculates selected-attribute and overall ranks over the complete fixed cohort; the browser only
  groups and highlights the bounded response.

## Completion notes

- **Completed:** 2026-07-14 in
  [PR #11](https://github.com/jimmie-potts/player-generator/pull/11), beginning with implementation
  commit `6849209`.
- **Delivered:** Added a deterministic representative endpoint and a comparison table grouped from
  highest to lowest talent tier. The default is three players from each of the five populated tiers
  in the local 2026 package (15 total), configurable from one through three per tier. Normalized
  partial-name and stable-`playerId` search can add and remove up to ten independent session pins
  without replacing the tier sample.
- **Comparison semantics:** Each row shows baseline and preview values, absolute delta, and baseline,
  preview, and movement ranks for the selected attribute and overall. The API uses minimum-rank tie
  semantics over the same complete baseline/preview cohort. The client highlights every tied largest
  positive or negative attribute change and distinguishes no change, missing input, exclusion, and
  preview failure.
- **Approved deviation:** The original top-overall-only default would overrepresent elite players.
  The revised acceptance criterion and
  [D-026](../DECISIONS.md#d-026-server-authoritative-designer-proposals-and-tiered-comparison)
  adopt three highest-ranked eligible players per populated tier while reserving ten of the API's
  25 selected-player slots for pins. The table preserves deterministic tier/rank order and uses
  largest-change signals instead of resorting rows after each edit.
- **Validation:** `.venv/bin/python -m pytest` passed 376 tests;
  `.venv/bin/python -m ruff check .`, `npm run workbench:build`, and `git diff --check` passed;
  `npm run workbench:test` passed 32 tests. API tests cover tier ordering, complete-cohort selected-
  attribute ranks and tied ranks; integration tests cover all five default groups, search, pin and
  unpin, retained defaults, largest gain/loss signals, and failure clearing. A live smoke test
  returned baseline ranks `1/2/3`, `12/12/12`, `33/33/33`, `85/85/85`, and `183/183/183` across the
  five groups.
- **Follow-ups:** Saved comparison groups and collaborative sharing remain deliberately out of
  scope. Pins disappear with the browser session.
- **Learnings:** Tier stratification reveals sensitivity across the rating curve without changing
  percentile populations, and ranks must remain server-owned and cohort-wide rather than depend on
  the displayed sample. These findings are recorded in
  [LEARNINGS.md](../LEARNINGS.md#2026-07-14--us-013).
