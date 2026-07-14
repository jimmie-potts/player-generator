# US-012: Preview formula adjustments

- **Status:** complete
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

- **2026-07-14:** Began after the US-011 inspection path and API context guards passed their
  acceptance tests. Per the approved [D-026](../DECISIONS.md#d-026-server-authoritative-designer-proposals-and-tiered-comparison)
  scope, the editor changes only existing component weights and directions, complete rating-scale
  anchor lists, and a designer-supplied proposal version.
- **2026-07-14:** Kept provisional validation and delta construction in React, but retained the API
  as the only formula validator and evaluator. A successful response owns the exact full document
  offered for export.
- **2026-07-14 review follow-up:** Preserved `AbortError` when cancellation occurs while the client
  is reading a response body, so every cancellation point honors the same no-error contract.

## Completion notes

- **Completed:** 2026-07-14 in
  [PR #11](https://github.com/jimmie-potts/player-generator/pull/11), beginning with implementation
  commit `6849209`.
- **Delivered:** Added session-only controls for every existing component weight, inverse direction,
  complete percentile-anchor curve, and proposal formula version. The workbench validates obvious
  form errors immediately, sends only supported deltas, and renders API-owned baseline and preview
  calculation details and absolute changes. Attribute reset restores its components and shared
  scale; reset-all restores the complete editor and initial proposal version.
- **Request correctness:** Previews wait 350 ms after an edit, abort superseded requests, ignore a
  late response even if its transport does not honor abort, and clear prior results during pending,
  invalid, stale, or failed states. Controls remain editable during calculation so rapid tuning can
  supersede in-flight work.
- **Export and reversibility:** Export is enabled only for the latest successful response and writes
  its exact formatted `previewDocument`, including the designer-supplied version, to a JSON download
  accepted by `roster-generator generate --formula`. The client exposes no write endpoint, preset,
  local-storage, approval, or deployment behavior; reload and close discard the React session.
- **Performance:** A live local request over the configured 582-player 2026 cohort, with all 15
  default representatives and their explanation trees selected, completed in 191 ms. The existing
  automated 1,000-player API gate remains bounded by the accepted 3,000 ms cross-environment budget.
- **Deviations and decisions:** [D-026](../DECISIONS.md#d-026-server-authoritative-designer-proposals-and-tiered-comparison)
  fixes the supported editing and exact-export scope;
  [D-027](../DECISIONS.md#d-027-session-scoped-client-state-with-cancellable-authoritative-previews)
  records in-memory state, context verification, debounce, cancellation, and response-owned export.
  Arbitrary metrics and expressions were deliberately not added.
- **Validation:** `.venv/bin/python -m pytest` passed 376 tests;
  `.venv/bin/python -m ruff check .`, `npm run workbench:build`, and `git diff --check` passed;
  `npm run workbench:test` passed 35 tests. A clean `npm ci` verifies that the root-owned jsdom test
  environment resolves from the hoisted Vitest runner on the repository's Node 22.12 CI baseline.
  Editor and integration tests cover valid and invalid weights, direction and anchor changes, rapid
  edits, late responses, reset, exact export, API failure, and explicit missing values.
- **Follow-ups:** Named proposals, persistence, approvals, deployment, and arbitrary expressions
  require later product scope and are not implied by the exported file.
- **Learnings:** Cancellation is a calculation-correctness mechanism as well as a performance tool,
  including while response bodies are being consumed, and a portable proposal should serialize the
  server's validated merge rather than reconstruct it from browser deltas. These findings are
  recorded in [LEARNINGS.md](../LEARNINGS.md#2026-07-14--us-012).
