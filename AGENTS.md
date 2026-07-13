# Repository guidance

These instructions apply to the entire repository. Preserve explicit user scope and keep unrelated
working-tree changes intact.

## Current state and planned state

The implemented project is currently one Python package under `src/player_generator/`. Its CLI,
configuration, source manifest, and current output paths remain authoritative until version 2
stories are implemented.

The approved redesign is documented in [docs/planning/README.md](docs/planning/README.md). It plans
two data subprojects—reference-data building and roster generation—plus a supporting React
workbench and Python preview API. Planning documents are specifications, not evidence that proposed
paths, commands, contracts, or applications already exist.

Until the user explicitly starts an implementation story, redesign work is documentation-only. Do
not edit runtime code, configuration, schemas, generated outputs, or pipeline behavior merely to
make them resemble the plan.

## Domain language

- Use `reference data` for actual-player source and derived calibration data.
- Use `roster data` for player-generator output.
- Use the same `player`, `team`, and `coach` entity vocabulary in both domains.
- Avoid identity qualifiers in new names and prose. When an existing legacy identifier must be
  referenced, label it as a current legacy interface and state its planned replacement.
- Neutral terminology does not remove the provenance boundary: source identity and source IDs stay
  in reference data and never appear in roster packages.

## Planned architecture boundaries

- The reference-data application owns local source registration, adapters, reconciliation,
  canonical normalization, provenance, and reference CSV publication.
- The roster generator consumes only a versioned published reference package. It must not read raw
  Parquet or import source adapters.
- `data-contracts` owns versioned schemas, keys, types, and relationship validation.
- `attribute-engine` is the only formula evaluator used by batch generation and the preview API.
- The workbench calls the preview API and must not reimplement rating calculations in TypeScript.
- The first version 2 roster package is player-only. Coach and team contracts are future design
  targets, not permission to populate those files.

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
- Use camelCase CSV headers, UTF-8, ISO 8601 dates, and stable internal IDs in planned version 2
  interfaces.
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
```

For current Python changes, run:

```bash
python -m pytest
python -m ruff check .
```

`python -m pytest` is the check currently enforced by CI. Mypy is installed as a development
dependency but is not yet an enforced repository check.

For documentation-only changes, run at minimum:

```bash
git diff --check
```

Also inspect Markdown links and verify that current paths are not presented as planned paths or the
reverse. Pipeline commands require local ignored source data and may rewrite tracked example
outputs; run them only when the active story requires it, then inspect the diff.

## Generated files and integrity metadata

- Do not hand-edit generated artifacts when their owning generator or schema should make the change.
- Preserve unrelated local changes and never add ignored reference files to Git.
- `FILE_MANIFEST.sha256` is a tracked snapshot of file hashes but has no automated validator in the
  repository. Keep it synchronized when intentionally maintaining it; otherwise create an explicit
  decision to retire it rather than silently relying on stale entries.
