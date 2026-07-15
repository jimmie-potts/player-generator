# Repository guidance

These instructions apply to the entire repository. Preserve explicit user scope and keep unrelated
working-tree changes intact.

## Current state and planned state

The implemented monorepo has two Python data applications under `apps/reference-data/` and
`apps/roster-generator/`, a React formula-design client and Python preview API under
`apps/formula-workbench/`, and shared Python packages under `packages/data-contracts/` and
`packages/attribute-engine/`.

The remaining redesign is documented in [docs/planning/README.md](docs/planning/README.md). Planning
documents describe future behavior unless their stories are marked complete. The reference builder
now supports registered local inputs, canonical normalization, and version 1 CSV publication with
season-relative attributes; its pinned download and wide tables remain standalone legacy
interfaces. The roster generator consumes only a validated published reference package and
atomically emits the normalized player-only roster package. Player attributes use the versioned
declarative formula and shared Python evaluator. The preview API reads one integrity-checked
reference cohort and exposes read-only version 1 endpoints. The React client supports
server-authoritative formula inspection, session-only tuning, tiered player comparison and pinning,
and validated JSON proposal export; it does not persist or deploy changes.

Do not implement a later story until the user explicitly starts it. Avoid changing runtime code,
configuration, schemas, outputs, or pipeline behavior merely to resemble an unstarted plan.

## Domain language

- Use `reference data` for actual-player source and derived calibration data.
- Use `roster data` for player-generator output.
- Use the same `player`, `team`, and `coach` entity vocabulary in both domains.
- Avoid identity qualifiers in new names and prose. When an existing legacy identifier must be
  referenced, label it as a current legacy interface and state its planned replacement.
- Neutral terminology does not remove the provenance boundary: source identity and source IDs stay
  in reference data and never appear in roster packages.

## Architecture boundaries

- The reference-data application owns local source registration, adapters, reconciliation,
  canonical normalization, provenance, and reference CSV publication.
- The roster generator consumes only a versioned published reference package. It must not read raw
  Parquet or import source adapters.
- `data-contracts` owns versioned schemas, keys, types, and relationship validation.
- `attribute-engine` is the only formula evaluator used by batch generation and the preview API.
- The preview API reads only a validated published reference package. It must not import either data
  application, read raw Parquet, or write formula, package, or preset state.
- The workbench calls the preview API and must not reimplement rating calculations in TypeScript.
- The normalized roster package is player-only. Coach and team contracts are future design targets,
  not permission to populate those files.

## User stories, decisions, and learnings

Use the workflow in
[docs/planning/USER_STORY_WORKFLOW.md](docs/planning/USER_STORY_WORKFLOW.md).

- Confirm dependencies before starting a story and change its status to `in_progress`.
- Treat acceptance criteria and explicit out-of-scope items as binding.
- Add dated implementation notes while work is active.
- Do not mark a story `complete` until every acceptance criterion passes and its completion notes
  include the date, PR or commit, delivered behavior, deviations, validation commands and results,
  follow-ups, decisions, and learnings.
- Record changed architectural choices in
  [docs/planning/DECISIONS.md](docs/planning/DECISIONS.md); never silently rewrite an accepted
  decision.
- Append reusable implementation findings to
  [docs/planning/LEARNINGS.md](docs/planning/LEARNINGS.md).
- An epic is complete only after all of its required stories are complete.

## Git and pull-request handoff

- Treat completion of a story, epic, or other logical unit of work as authorization to commit its
  intended files, push the working branch, and open a pull request without waiting for another
  user prompt, unless the user explicitly requests local-only work or says not to publish it.
- Open pull requests ready for review, not as drafts. If a publishing tool creates a draft, mark it
  ready before reporting the handoff complete.
- Pull-request handoff is non-blocking for the local implementation and story status. If GitHub
  authentication, network access, permissions, or another external condition prevents publication,
  preserve the validated commits, report the exact blocker, and retry when it clears; do not undo
  completed work or silently stop at a local commit.
- Use the repository's default branch as the base unless the user specifies another target. Give
  the pull request a concise title and a body covering scope, motivation, impact, and validation.
- Link the ready pull request from applicable story completion notes. Never include unrelated
  working-tree changes merely to complete a handoff.
- After a pushed change fully addresses a pull-request review thread, reply in that thread with a
  brief summary of the fix and relevant validation, then resolve the thread. Leave partially
  addressed or ambiguous feedback open and state what remains.

## Data and licensing

- Keep raw Parquet and transformed named reference tables local and untracked.
- Do not commit or redistribute third-party data without established rights.
- Record source type, path or filename, upstream version when known, SHA-256 hash, adapter/schema
  version, row counts, and license status.
- Keep source IDs and reconciliation mappings in reference output only. Never publish a
  source-to-roster crosswalk.
- Leave unavailable optional fields empty or omit them according to the contract; do not fabricate
  values without an approved rule.

## Contracts and determinism

- Govern every CSV header, key, type, null rule, enum, and relationship with a versioned contract.
- Maintain corresponding reference and roster `players.csv`, `player_stats.csv`, and
  `player_attributes.csv` definitions in parity. A shared field or CSV-formatting change must update
  both contract profiles, fixtures, validators, and documentation in the same story and pull
  request.
- Keep profile-only columns and files explicit. Reference season context, source identity, and
  provenance may remain reference-only; roster generation metadata may remain roster-only. Do not
  use a profile extension to create two definitions of the same shared field.
- Add cross-profile contract tests for shared ordered fields, types, base null rules and declared
  overrides, units, bounds, and serialization so parity cannot drift silently.
- Use camelCase CSV headers, UTF-8, ISO 8601 dates, and stable internal IDs in player data contract
  version 1 interfaces.
- Formula weights must be finite and nonnegative and normalize to 1. Ratings use the configured
  25–99 scale.
- Identical input files, contracts, formulas, configuration, and seed must produce identical data
  rows and content hashes.
- Write packages atomically only after contract and relationship validation succeeds.

## Current commands and validation

Set up the current implementation with:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
npm install
```

Run the local preview API against the configured ignored reference package with:

```bash
formula-preview-api --config apps/formula-workbench/api/config/default.yaml
# or: make formula-api
```

For current Python changes, run:

```bash
python -m pytest
python -m ruff check .
npm run workbench:test
npm run workbench:build
```

Python tests, Ruff, workbench tests, and the workbench build are enforced by CI. Mypy is installed as
a development dependency but is not yet an enforced repository check.

For documentation-only changes, run at minimum:

```bash
git diff --check
```

Also inspect Markdown links and verify that current paths are not presented as planned paths or the
reverse. Reference and roster package commands write ignored local outputs; never stage those
packages or their named reference inputs.

## Generated files and integrity metadata

- Do not hand-edit generated artifacts when their owning generator or schema should make the change.
- Preserve unrelated local changes and never add ignored reference files to Git.
- `FILE_MANIFEST.sha256` is a tracked snapshot of file hashes. `tests/test_file_manifest.py`
  verifies that its entries are sorted, cover every other tracked file, and match current content.
  After staging intended additions and deletions, run `make manifest` to synchronize it with every
  intentional tracked-file change, then stage the regenerated `FILE_MANIFEST.sha256`.
