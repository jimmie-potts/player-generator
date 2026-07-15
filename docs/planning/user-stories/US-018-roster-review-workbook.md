# US-018: Generate a roster review workbook

- **Status:** ready
- **Epic:** [EPIC-08](../epics/EPIC-08-nba-gm-mvp-handoff.md)
- **Dependencies:** US-017

## User story

As a roster reviewer, I want a generated workbook organized for human inspection so that I can
review players, statistics, attributes, and validation evidence without treating a wide CSV as the
canonical integration source.

## Acceptance criteria

- Generate `roster-review.xlsx` only from an already validated canonical roster package.
- Keep the workbook outside the canonical package directory and outside manifest file-set and hash
  coverage. It must not change the source package or participate in its content hash.
- Provide `Players`, `Box Stats`, `Advanced Metrics`, `Attributes`, and `Validation Summary`
  worksheets.
- Project `Box Stats` and `Advanced Metrics` from the roster profile's one canonical
  `player_stats.csv` using the shared field classifications completed by US-016. Do not introduce a
  workbook-only interpretation of a field shared with the reference profile.
- Include the source package contract identifier, content hash, formula identity, row counts, and
  season-ending-year convention in `Validation Summary`.
- Use values only: no macros, executable formulas, external links, hidden content, or workbook-to-
  package write-back.
- Preserve deterministic row and column ordering and fail before writing when the source package is
  invalid.
- Document the workbook as a generated, noncanonical, read-only review artifact.

## Out of scope

- NBA-GM ingestion from XLSX.
- Accepting workbook edits as package changes.
- Replacing or supplementing canonical CSV validation.
- ESPN-derived simulation statistics, deeper metrics, personality data, and simulation context.

## Validation

- Tests verify sheet names, ordered headers, row counts, values, and package-content-hash traceability.
- Invalid or tampered source packages produce no workbook.
- Security checks verify that the workbook contains no macros, formulas, external links, or hidden
  worksheets.
- Render and inspect representative sheets for readable frozen headers, filters, numeric formats,
  and validation presentation.
- Run `git diff --check` and the repository checks affected by the chosen workbook library.

## Implementation notes

Append dated notes here while the story is active. This story is optional and must not block the
machine-to-machine NBA-GM MVP handoff.

## Completion notes

Pending. Record the generator command, output location, source-hash traceability, visual and
security validation, pull request or commit, deviations, follow-ups, decisions, and learnings before
changing status to `complete`.
