# US-008: Consume a published reference package

- **Status:** ready
- **Epic:** [EPIC-04](../epics/EPIC-04-roster-package.md)
- **Dependencies:** US-005, US-007

## User story

As a game developer, I want roster generation to consume a published reference package so that it
does not depend on raw sources or adapter internals.

## Acceptance criteria

- The roster-generator CLI accepts a reference-package directory and roster configuration.
- It validates the package manifest, required files, content hash, contract versions, key
  relationships, and compatible formula version before sampling.
- It never imports source adapters or reads upstream Parquet files.
- Eligibility filters, season selection, recency weights, roster size, and random seed are explicit
  configuration.
- Validation failures identify the incompatible file, contract, or relationship before generation
  starts.
- Identical reference package, configuration, formula document, and seed select the same templates.

## Out of scope

- Building or repairing a reference package automatically.

## Validation

- Integration fixtures cover valid packages, missing files, hash mismatch, unsupported versions,
  orphan IDs, empty eligible populations, and deterministic template selection.

## Implementation notes

Append dated notes here while the story is active.

## Completion notes

Pending. Record accepted contract versions, CLI behavior, determinism evidence, and validation
results before changing status to `complete`.
