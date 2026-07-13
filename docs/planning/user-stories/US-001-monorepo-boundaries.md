# US-001: Establish the monorepo boundaries

- **Status:** complete
- **Epic:** [EPIC-01](../epics/EPIC-01-project-structure.md)
- **Dependencies:** none

## User story

As a contributor, I want reference building, roster generation, and formula exploration isolated so
that each responsibility can evolve and be tested independently.

## Acceptance criteria

- Create independently runnable `reference-data`, `roster-generator`, and `formula-workbench`
  applications in one repository.
- Treat reference data and roster generation as the two data subprojects; the workbench and API are
  supporting applications over their shared contracts and formula engine.
- Put versioned schemas and validation in `data-contracts` and shared calculation behavior in
  `attribute-engine`.
- Reference-data code does not import roster-generation code.
- Roster generation consumes only a published reference package.
- Each application has its own entry point, configuration boundary, tests, and documentation.
- Root commands can run each application and the complete test suite from a fresh checkout.
- Current version 1 behavior remains clearly labeled until it is replaced.

## Out of scope

- New source adapters, output schemas, formulas, or UI behavior.
- Compatibility wrappers for version 1 commands or paths.

## Validation

- Import-boundary tests fail on prohibited dependencies.
- Clean-install tests exercise each application entry point.
- Documentation link and command checks pass.

## Implementation notes

### 2026-07-12

- Began restructuring the current pipeline into independently runnable reference-data,
  roster-generator, and formula-workbench applications.
- The existing formulas and schema constants will move without behavioral changes into the planned
  shared packages; new source adapters, output contracts, and formula behavior remain out of scope.
- Completed the split using one root Python distribution with multiple source roots, two independent
  Python CLIs, separate app configuration, shared contract and attribute packages, and an npm
  workspace for the workbench shell.
- Added AST import-boundary tests so the data applications cannot import one another and shared
  packages cannot import applications.
- Review follow-up restored clean-checkout orchestration by making the aggregate root command
  download or verify reference data before building it, tightened roster relationship validation,
  and aligned the declared Node.js floor with Vite 7.

## Completion notes

- **Completed:** 2026-07-12
- **Branch:** `agent/implement-us-001-us-002`; [PR #3](https://github.com/jimmie-potts/player-generator/pull/3).
- **Delivered:** Independent `reference-data`, `roster-generator`, and formula-workbench entrypoints;
  separate application configs/tests/READMEs; shared `data-contracts` and `attribute-engine` package
  ownership; root install/test/build commands; and CI coverage for Python and frontend boundaries.
- **Accepted deviation:** The roster generator consumes the current processed player-season CSV as
  a transitional published seam. Package manifests and normalized reference contracts remain
  US-005 and US-008 work and are not claimed here.
- **Accepted deviation:** The workbench is a static React shell with no API or formula behavior,
  preserving the EPIC-05 and EPIC-06 boundaries.
- **Validation:** Fresh local Python editable install; npm install with zero reported
  vulnerabilities; Python tests including aggregate-command and contract relationship regressions;
  Ruff; both console `--help` entrypoints; workbench test and production build; complete reference
  build, roster generation, and comparison commands.
- **Follow-up:** US-003 begins local Parquet registration. US-005 and US-008 replace the transitional
  processed-CSV seam with versioned packages. US-006 makes formulas declarative.
- **Learning:** Setuptools multi-root discovery preserves one clean root install while keeping
  application imports physically isolated; the boundary test is the durable enforcement mechanism.
