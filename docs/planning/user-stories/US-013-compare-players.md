# US-013: Compare representative players

- **Status:** ready
- **Epic:** [EPIC-06](../epics/EPIC-06-workbench.md)
- **Dependencies:** US-012

## User story

As a designer, I want to compare formula effects across representative players so that tuning is not
based on one example.

## Acceptance criteria

- Show a configurable number of players ranked highest by baseline overall by default.
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

- Tests cover default ranking, search normalization, pinning, delta sorting, tied ranks, missing
  players, and session reset.

## Implementation notes

Append dated notes here while the story is active.

## Completion notes

Pending. Record sample size, ranking conventions, UI tests, and tuning learnings before changing
status to `complete`.
