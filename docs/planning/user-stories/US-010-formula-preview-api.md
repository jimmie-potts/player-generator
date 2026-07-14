# US-010: Provide formula and player preview endpoints

- **Status:** in_progress
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
  minimum-rank ties, and a 2,000 ms warm recalculation budget.
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

## Completion notes

Pending. Record endpoint contracts, sample bounds, latency results, commands, and learnings before
changing status to `complete`.
