# US-002: Adopt neutral domain terminology

- **Status:** complete
- **Epic:** [EPIC-01](../epics/EPIC-01-project-structure.md)
- **Dependencies:** US-001

## User story

As a contributor, I want consistent reference and roster terminology so that entities use the same
domain vocabulary regardless of provenance.

## Acceptance criteria

- Use `reference data`, `roster data`, `player`, `team`, and `coach` in new interfaces and prose.
- Remove deprecated identity qualifiers from filenames, paths, CLI text, package metadata, schemas,
  comments, errors, tests, examples, and documentation.
- Move the legacy output directory to `roster_data/` and replace its identity-qualified flattened
  player filename as part of the version 2 contract migration.
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

### 2026-07-12

- Began replacing deprecated identity-qualified paths, filenames, CLI text, package metadata,
  schemas, fixtures, and documentation with reference/roster terminology.
- Provenance and identity-leak protections remain unchanged while names and paths are migrated.
- Moved tracked output to `roster_data/`, renamed the flat output to `players.csv`, replaced the
  coupled CLI and package metadata, and regenerated reports with roster/reference field names.
- Removed deprecated identity qualifiers from tracked source, configuration, schema, fixtures,
  generated examples, and user-facing documentation.

## Completion notes

- **Completed:** 2026-07-12
- **Branch:** `agent/implement-us-001-us-002`; [PR #3](https://github.com/jimmie-potts/player-generator/pull/3).
- **Delivered:** Neutral app/package metadata and CLI help; `roster_data/default_roster.json` and
  `roster_data/players.csv`; neutral roster schema title and generator messages; roster-oriented
  comparison JSON keys and CSV headers; and updated README, notices, data documentation, and
  contributor guidance.
- **Migration impact:** The old combined CLI, old output directory, identity-qualified flat CSV,
  root config, and script wrappers were removed as the approved clean break. Consumers must use the
  two new CLIs and roster paths.
- **Validation:** Repository content search found no deprecated identity qualifiers or old output
  path; path search found no retained old output filenames; Python tests, Ruff, entrypoints,
  workbench checks, and regenerated comparison outputs passed.
- **Follow-up:** Later stories may change roster filenames again when the normalized player-only
  package is introduced, but must retain the reference/roster vocabulary and provenance boundary.
- **Learning:** Renaming the data domain also changes machine-readable comparison keys and report
  headers; regenerating owned artifacts and checking downstream vocabulary must be one operation.
