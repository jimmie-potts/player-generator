# US-002: Adopt neutral domain terminology

- **Status:** ready
- **Epic:** [EPIC-01](../epics/EPIC-01-project-structure.md)
- **Dependencies:** US-001

## User story

As a contributor, I want consistent reference and roster terminology so that entities use the same
domain vocabulary regardless of provenance.

## Acceptance criteria

- Use `reference data`, `roster data`, `player`, `team`, and `coach` in new interfaces and prose.
- Remove deprecated identity qualifiers from filenames, paths, CLI text, package metadata, schemas,
  comments, errors, tests, examples, and documentation.
- Rename `generated_data/` to `roster_data/` and replace the current flattened player filename as
  part of the version 2 contract migration.
- Preserve the provenance boundary: source IDs and actual-player mappings remain reference-only.
- Update the root README, data READMEs, notices, configuration, and contributor instructions.
- A repository search finds no deprecated terminology except historical decision or migration notes
  that explicitly require it.

## Out of scope

- Changing generation algorithms.

## Validation

- Terminology search over tracked files.
- Current and planned command/path documentation matches implemented behavior after migration.

## Implementation notes

Append dated notes here while the story is active.

## Completion notes

Pending. Record renamed interfaces, migration impact, validation, decisions, and learnings before
changing status to `complete`.
