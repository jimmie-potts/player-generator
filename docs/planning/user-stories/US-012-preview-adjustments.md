# US-012: Preview formula adjustments

- **Status:** ready
- **Epic:** [EPIC-06](../epics/EPIC-06-workbench.md)
- **Dependencies:** US-011

## User story

As a designer, I want to adjust supported formula controls in real time so that I can see their
effect before proposing a configuration change.

## Acceptance criteria

- Allow temporary edits to component weights, inverse direction, and percentile anchors.
- Validate changes in the client for immediate feedback and rely on the API as the authoritative
  validator.
- Display baseline, preview, absolute delta, and calculation breakdown for the selected attribute.
- Debounce or cancel superseded requests so stale responses cannot replace newer results.
- Provide reset for an attribute and reset-all for the session.
- Export a versioned proposed formula document that passes API validation.
- Reloading or closing the application discards edits.
- The workbench cannot overwrite active configuration or save named presets.

## Out of scope

- Arbitrary expressions, persistent editing, approvals, or formula deployment.

## Validation

- Tests cover valid and invalid weights, direction changes, anchor ordering, rapid edits, stale
  responses, reset, export, and failed API requests.

## Implementation notes

Append dated notes here while the story is active.

## Completion notes

Pending. Record interaction decisions, export format, performance results, commands, and learnings
before changing status to `complete`.
