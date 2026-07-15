# US-010: Provide formula and player preview endpoints

- **Status:** complete
- **Epic:** [EPIC-05](../epics/EPIC-05-formula-api.md)
- **Dependencies:** US-005, US-007

## User story

As a frontend developer, I want a read-only formula API so that the browser can inspect and preview
the authoritative calculations without reimplementing them.

## Acceptance criteria

- Expose versioned endpoints for the active formula document, available metric metadata, baseline
  player results, player search, player calculation detail, and temporary previews.
- Preview requests accept changed component weights, inverse direction, and percentile anchors plus
  selected player IDs.
- Preview responses include baseline value, preview value, delta, rank movement, raw inputs,
  percentiles, normalized weights, contributions, and validation errors.
- Search supports normalized partial player names and stable player IDs.
- The default baseline sample is bounded and ranked by baseline overall; requested pinned players
  can be added to it.
- Recalculation uses the shared attribute engine and an explicitly identified reference-package and
  formula version.
- Preview endpoints do not write formula configuration, reference data, or presets.
- Invalid requests return structured field-level errors without partial results.

## Out of scope

- Authentication, persistence, formula deployment, and production infrastructure.

## Validation

- API contract tests cover formulas, metrics, search, detail, previews, invalid edits, missing
  players, package mismatch, and write prevention.
- Performance tests set an approved preview latency budget for the bounded sample.

## Implementation notes

- **2026-07-13:** Started after confirming US-005 and US-007 are complete and the batch-data
  foundation is merged on `main`. Scope is limited to the versioned, read-only Python API; React
  inspection and editing behavior remains in EPIC-06.
- **2026-07-13:** The implementation will load one explicitly configured season cohort from an
  integrity-checked reference package, evaluate the complete bounded cohort through
  `attribute-engine`, cache its baseline, and bound only returned samples. This preserves
  percentile semantics while keeping preview responses responsive.
- **2026-07-13:** Accepted [D-023](../DECISIONS.md#d-023-fastapi-preview-application-with-api-owned-contracts),
  [D-024](../DECISIONS.md#d-024-complete-configured-preview-cohort-with-bounded-responses), and
  [D-025](../DECISIONS.md#d-025-shared-package-integrity-with-active-formula-recalculation).
  The version 1 FastAPI/Pydantic contract uses one configured 2026 cohort, a 1,000-row cohort cap,
  a 25-player baseline sample, at most 25 pins or preview players, at most 20 search results,
  minimum-rank ties, and an initial 2,000 ms warm recalculation budget.
- **2026-07-13:** Version 1 exposes `GET /api/v1/formula`, `/metrics`, `/players`,
  `/players/search`, `/players/{playerId}`, and `POST /api/v1/previews`. Successful responses identify
  the reference package and active formula; preview requests echo those hashes as optimistic context
  tokens. Edits are request-local and limited to component weights, inverse direction, and complete
  named rating-scale anchor lists.
- **2026-07-13:** Endpoint shapes, bounds, errors, context tokens, configuration, and no-write
  behavior are documented in
  [apps/formula-workbench/api/README.md](../../../apps/formula-workbench/api/README.md). Completion
  status and validation evidence remain pending until every acceptance criterion passes.
- **2026-07-13:** Runtime audit tightened the request boundary: preview JSON accepts only strict
  camelCase fields and declared scalar types, each request must echo the configured `season`, and a
  stale season joins stale package or formula tokens in a structured `409 stale_context` response.
  The async preview route sends shared-engine evaluation to an application-owned two-worker
  executor, preserving event-loop responsiveness without relying on the sync-route/AnyIO or asyncio
  default-executor paths that hang on the repository's current Python 3.14 test stack.
- **2026-07-13:** PR validation measured the exact 1,000-player preview at 2,260 ms on GitHub's
  Python 3.12 runner. The approved warm budget was revised to 3,000 ms so the cross-environment gate
  has operating margin; the 1,000-row cohort cap and every response bound remain unchanged. This
  amendment is recorded under [D-024](../DECISIONS.md#d-024-complete-configured-preview-cohort-with-bounded-responses).
- **2026-07-14:** Approved a D-024 optimization that retains the complete configured cohort for
  temporary preview ratings, percentiles, and ranks while materializing preview explanation trees
  only for `selectedPlayerIds`. The response cannot expose unselected explanations, so this reduces
  unused nested-object work without changing calculation population or results.

## Completion notes

- **Completed:** 2026-07-13 in
  [PR #10](https://github.com/jimmie-potts/player-generator/pull/10), beginning with implementation
  commit `f4ac1a7`.
- **Delivered:** Added the read-only `/api/v1` formula, metric, baseline-player, normalized search,
  player-detail, and temporary-preview endpoints. Every success response identifies the loaded
  version 1 reference profile, active formula, configured season, and cohort size. Previews apply
  request-local weight, inverse-direction, and complete rating-anchor edits through the shared
  evaluator, then return selected players' baseline/preview rows, deltas, full-cohort rank movement,
  and authoritative calculation explanations without writing files.
- **Review optimization (2026-07-14):** Temporary previews continue to calculate ratings,
  percentiles, and ranks over the full cohort but now materialize explanation trees only for selected
  players. Local and GitHub validation for this amendment are tracked on
  [PR #10](https://github.com/jimmie-potts/player-generator/pull/10).
- **Bounds and latency:** The default response contains the top 25 players; requests allow at most
  25 unique pins or selected players and 20 search results. Startup rejects a season cohort over
  1,000 rows. The exact 1,000-player synthetic regression kept both in-process evaluation and HTTP
  wall time within the accepted 3,000 ms warm budget across local and GitHub validation.
- **Deviations and decisions:** [D-023](../DECISIONS.md#d-023-fastapi-preview-application-with-api-owned-contracts)
  selected FastAPI, Uvicorn, strict API-owned Pydantic models, and a bounded worker executor;
  [D-024](../DECISIONS.md#d-024-complete-configured-preview-cohort-with-bounded-responses) evaluates
  the full explicit season before bounding responses instead of evaluating only the displayed
  sample; and [D-025](../DECISIONS.md#d-025-shared-package-integrity-with-active-formula-recalculation)
  extracted consumer-independent reference integrity checks and permits an active formula to differ
  from the package's published formula while exposing both identities. Runtime audit also added the
  required season token, strict camelCase/no-coercion inputs, and nonblocking preview execution.
- **Validation:** `.venv/bin/python -m pytest` passed 364 tests; `.venv/bin/python -m ruff check .`,
  `npm run workbench:test`, `npm run workbench:build`, and `git diff --check` passed. The 40 API tests
  cover the complete contract, direct shared-engine parity, determinism, integrity/startup failures,
  stale context including season, invalid edits without partial results, write prevention, exact
  maximum-cohort latency, and read responsiveness during a blocked preview calculation.
- **Follow-ups:** Authentication, persistence, deployment, production infrastructure, React API
  integration, formula inspection/editing UI, and player comparison remain deliberately outside
  this story and are planned for EPIC-06 or later work.
- **Learnings:** Interactive response limits must not alter formula populations; package/formula/
  season identities form the stateless preview context; transport inputs need stricter validation
  than internal response construction; and CPU-bound evaluation needs a bounded worker boundary.
  These findings are recorded in [LEARNINGS.md](../LEARNINGS.md#2026-07-13--us-010).
