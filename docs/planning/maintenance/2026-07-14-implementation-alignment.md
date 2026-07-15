# 2026-07-14: Implementation alignment

- **Status:** complete
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

- `.venv/bin/python -m pytest` passed all 386 tests, including configuration regressions for exact,
  reduced, inherited, independently configured, and excessive version 1 limits.
- `.venv/bin/python -m ruff check .` passed.
- `TMPDIR=/tmp npm run workbench:test` passed all 85 frontend tests. `TMPDIR` avoids the Codex desktop
  WSL session's unavailable inherited Windows temporary directory; it does not change application
  behavior.
- `npm run workbench:build`, `sha256sum -c FILE_MANIFEST.sha256`, and staged and unstaged
  `git diff --check` passed.

## Completion notes

- **Completed:** 2026-07-14 in implementation commit `16d0e13` and ready-for-review
  [PR #12](https://github.com/jimmie-potts/player-generator/pull/12).
- **Delivered:** `PreviewSettings` now enforces the published version 1 ceilings for baseline, pin,
  selected-player, search, and cohort limits for YAML, replacements, and direct construction. The
  service uses the new `max_selected_players` setting independently of `max_pinned_players`, while
  older YAML that omits the new field inherits its pin limit. The Pydantic request model and settings
  use one selected-player maximum constant.
- **Documentation:** [D-030](../DECISIONS.md#d-030-formula-preview-version-1-bounds-are-contract-maxima)
  records the invariant; the API README documents configurable narrowing and legacy inheritance;
  and the reference-data configuration and README explicitly identify the legacy-only season and
  weighting block. `THIRD_PARTY_NOTICES.md` and its inbound links were removed at the user's
  direction while current data-rights rules and source metadata remain in their authoritative files.
- **Scope:** No endpoint payload, calculation, default limit, package contract, reference row, or
  roster behavior changed. EPIC-07 and US-014 remain `ready` and unstarted.
- **Follow-ups:** Runtime and dependency identity in deterministic reproduction remains a separate
  decision. US-014 is the next dependency-ready roadmap unit after this maintenance pull request.
- **Learnings:** Contract limits belong at settings construction rather than only in defaults;
  semantically distinct limits require separate names even when their values match; and mixed
  current/legacy configuration needs command ownership stated beside the fields. These findings are
  recorded in [LEARNINGS.md](../LEARNINGS.md#2026-07-14--implementation-alignment).
