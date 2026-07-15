# EPIC-01: Repository structure and terminology

- **Status:** complete
- **Outcome:** Separate application responsibilities and adopt reference/roster domain language.
- **Dependencies:** none

## Why

The current package couples ingestion, ratings, roster generation, reporting, and CLI orchestration.
The redesign needs enforceable boundaries before its data contracts and applications can evolve
independently.

## Stories

- [US-001: Establish the monorepo boundaries](../user-stories/US-001-monorepo-boundaries.md)
- [US-002: Adopt neutral domain terminology](../user-stories/US-002-neutral-terminology.md)

## Success criteria

- The planned applications and shared packages are independently testable.
- Reference building does not depend on roster generation.
- Current behavior remains truthfully documented throughout delivery.
- Deprecated terminology is removed from user-facing and implementation surfaces.

## Non-goals

- Implementing new adapters, data contracts, formulas, or web features.
- Retaining wrapper interfaces for superseded commands and outputs.

## Risks

- Moving files before boundaries are defined could reproduce the same coupling under new paths.
- Documentation can accidentally describe planned paths as already runnable.
