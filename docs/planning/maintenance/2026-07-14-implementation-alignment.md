# 2026-07-14: Implementation alignment

- **Status:** in_progress
- **Scope:** Resolve the bounded-API and documentation discrepancies found after EPIC-06 without
  starting EPIC-07 or US-014.
- **Dependencies:** EPIC-01 through EPIC-06 and US-015

## Findings being aligned

- The default formula preview configuration follows the published version 1 limits, but alternate
  configuration can raise some response and cohort bounds beyond that contract. Preview selection
  also reuses the pin-limit setting even though pins and selected preview players are separate API
  concepts.
- The reference-data configuration does not label its `reference` season and weighting block as
  legacy-build-only, even though normalized publication intentionally processes every canonical
  player-season from registered inputs.
- The standalone third-party notice duplicates safeguards recorded in current data-boundary and
  source-manifest documentation and contains stale adapter roadmap prose.

## Acceptance checks

- Treat the version 1 maxima of 25 baseline players, 25 request pins, 25 selected preview players,
  20 search results, and 1,000 cohort rows as contract invariants that configuration may lower but
  cannot raise.
- Give selected preview players an explicit configuration setting while preserving existing custom
  configurations that only declare the pin limit.
- Cover default, reduced, legacy-compatible, and above-contract configuration values with tests.
- Document the fixed bounds in the API contract and decision log.
- Label the reference-data `reference` block as legacy-build-only in configuration and application
  documentation.
- Remove `THIRD_PARTY_NOTICES.md` and every inbound link while preserving data-rights guidance in
  the root README, data-boundary documentation, and tracked source manifest.
- Leave US-014 and EPIC-07 at `ready`; do not add team or coach contracts or generation behavior.

## Out of scope

- Changing endpoint payloads, formula calculations, response populations, or default limits.
- Changing normalized reference rows, package contracts, or publication behavior.
- Defining or generating teams and coaches.
- Expanding deterministic manifests with runtime or dependency identity; that separate ambiguity
  requires its own reproducibility decision.

## Validation

Pending implementation. Run the complete Python and frontend suites, Ruff, the production
workbench build, manifest integrity verification, and diff checks before completion.

## Completion notes

Pending. Record delivered behavior, validation results, commit or pull request, deviations,
follow-ups, decisions, and learnings before changing status to `complete`.
