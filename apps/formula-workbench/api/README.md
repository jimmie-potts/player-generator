# Formula preview API

This Python application is the read-only calculation boundary for the formula workbench. It loads
one integrity-checked version 2 reference package, keeps one configured season cohort in memory, and
uses `player_attribute_engine` for both the cached baseline and every temporary preview. The API does
not read Parquet, import source adapters, or implement rating calculations itself.

US-010 is complete. The HTTP contract below is version 1 and is owned by the API's Pydantic models
and generated OpenAPI document. The React client does not consume it until EPIC-06.

## Run locally

Publish or select a local reference package first. The default configuration expects the ignored
package at `reference_data/packages/reference-v2`.

```bash
formula-preview-api --config apps/formula-workbench/api/config/default.yaml
```

Equivalent commands are:

```bash
python -m formula_preview_api --config apps/formula-workbench/api/config/default.yaml
make formula-api
```

The server binds to `127.0.0.1:8000` by default. Use `--host`, `--port`,
`--reference-package`, or `--season` for local overrides. FastAPI serves interactive documentation
at `/docs` and the generated OpenAPI contract at `/openapi.json`.

The default YAML configuration is:

```yaml
paths:
  reference_package_dir: reference_data/packages/reference-v2

preview:
  season: 2026
  default_sample_size: 25
  max_pinned_players: 25
  max_search_results: 20
  max_cohort_size: 1000
  latency_budget_ms: 3000
```

Startup fails before serving requests when the package, its manifest, exact file set, hashes, row
counts, contracts, relationships, or configured cohort is invalid. The full configured season is
evaluated so shooting priors and percentiles retain their declared population. The 1,000-row bound
applies to that in-memory cohort; the smaller sample, pin, and search limits bound response work.

## Version and context tokens

Every successful response contains a `context` object:

```json
{
  "apiVersion": "1",
  "referencePackage": {
    "packageVersion": 2,
    "contentHash": "<reference package SHA-256>",
    "publishedFormulaVersion": "1.0.0",
    "publishedFormulaDocumentHash": "<published formula SHA-256>"
  },
  "formula": {
    "schemaVersion": 1,
    "formulaVersion": "1.0.0",
    "documentHash": "<active formula SHA-256>"
  },
  "season": 2026,
  "cohortSize": 376
}
```

The package's published formula identifies its stored `player_attributes.csv` snapshot. The active
formula identifies the calculation the API actually evaluates. They may differ. When the published
version and exact document hash match the active formula, startup also verifies that the published
attributes match a fresh shared-engine evaluation.

Preview requests must echo `apiVersion`, `referencePackage.contentHash`, `formula.formulaVersion`,
`formula.documentHash`, and the configured `season`. A changed token produces `409 stale_context`
before any calculation, so a browser cannot show a preview against a package, formula, or cohort
different from the baseline it received.

## Endpoints

### `GET /api/v1/formula`

Returns `context` and a copy of the complete active declarative formula document. The document is
inspectable but cannot be overwritten through this API.

### `GET /api/v1/metrics`

Returns `context` and ordered metric metadata. Each metric includes its name, generated label and
description, kind, source field or derived inputs, derivation settings, and every attribute use with
the configured weight and direction.

### `GET /api/v1/players`

Returns the top baseline sample for the configured season. With no query parameters the response is
limited to 25 players, ordered by overall descending and then stable player ID. Overall ties use the
minimum occupied rank, so tied values have the same rank while the ID affects display order only.
Players without an overall rating sort after ranked players.

`limit` may reduce the default sample to `1..25`. Repeat `pinnedPlayerId` to append as many as 25
unique players that are not already in the sample:

```text
GET /api/v1/players?limit=10&pinnedPlayerId=player-001&pinnedPlayerId=player-002
```

Pins are request-only and are never saved. An unknown, duplicate, or excessive pin rejects the whole
request.

### `GET /api/v1/players/search`

Searches display names and stable reference player IDs within the configured season:

```text
GET /api/v1/players/search?q=duren&limit=10
```

Search normalizes text with Unicode NFKC, case folding, and removal of non-alphanumeric characters,
then performs a partial match. Exact IDs and name prefixes sort before other matches, followed by
baseline rank and stable name/ID order. `q` must contain searchable text, and `limit` is `1..20`.
Source IDs and reconciliation mappings are never exposed.

### `GET /api/v1/players/{playerId}`

Returns the player's baseline row and the authoritative shared-engine calculation detail: eligibility
and reasons, cohort values and size, raw inputs, metric derivations, component percentiles,
normalized weights, contributions, composite, composite percentile, and final rating. The player
must exist in the configured season cohort.

### `POST /api/v1/previews`

Evaluates a temporary deep copy of the active formula over the same complete season cohort and
returns results only for the selected players. A request has this shape:

```json
{
  "apiVersion": "1",
  "referencePackageHash": "<context.referencePackage.contentHash>",
  "formulaVersion": "<context.formula.formulaVersion>",
  "formulaDocumentHash": "<context.formula.documentHash>",
  "season": 2026,
  "selectedPlayerIds": ["player-001"],
  "adjustments": {
    "components": [
      {
        "attribute": "overall",
        "metric": "playerImpactEstimate",
        "weight": 0.4,
        "inverseDirection": false
      }
    ],
    "ratingScales": [
      {
        "scale": "overall",
        "anchors": [
          {"percentile": 0.0, "rating": 50},
          {"percentile": 1.0, "rating": 97}
        ]
      }
    ]
  }
}
```

Preview JSON is strict camelCase. Snake-case aliases, unknown fields, numeric strings, integer-like
floats, and other scalar coercions are rejected instead of being normalized silently. Clients must
send JSON values with the types published by the OpenAPI contract.

At least one and at most 25 unique selected player IDs are required. A component adjustment targets
an existing `(attribute, metric)` pair and may supply a nonnegative `weight`,
`inverseDirection`, or both. `inverseDirection: true` flips the active component direction;
`false` retains it. The shared formula validator requires every attribute's adjusted weights to have
a positive sum and normalizes them to 1.

A rating-scale adjustment replaces the complete anchor list for a named scale. It is deliberately
scale-wide: every attribute that references the scale observes the temporary anchors. Anchors must
remain strictly ordered, span percentiles 0 and 1, map monotonically within 25–99, and satisfy the
shared formula contract. Eligibility, cohorts, metric expressions, output fields, talent tiers, and
active formula configuration are not editable endpoints.

The response includes the active `context`, a `previewFormulaHash` for the ephemeral edited document,
warm evaluation time, and each selected player's baseline and preview rows. `changes` records the
baseline value, preview value, and numeric delta for every rating output. Baseline and preview
calculation details contain the raw inputs, percentiles, normalized weights, and contributions.
Baseline rank, preview rank, and `rankMovement` are calculated over the same full cohort; positive
movement means the player moved toward rank 1.

The approved warm calculation budget is 3,000 ms for a configured cohort of at most 1,000 players.
It measures the in-process shared-engine recalculation and excludes package loading and server
startup. The async preview handler explicitly dispatches its CPU-bound evaluation to an
application-owned executor with two bounded workers. Formula, metric, baseline, search, and detail
requests can therefore continue on the event loop while recalculation runs in a worker thread.

## Error contract

Invalid requests never return partial player or calculation results. Errors use one shape:

```json
{
  "error": {
    "code": "invalid_request",
    "message": "Preview request validation failed.",
    "fields": [
      {
        "path": "selectedPlayerIds",
        "code": "missing_player",
        "message": "Player was not found."
      }
    ]
  }
}
```

- `404 player_not_found` identifies an unavailable detail player.
- `409 stale_context` identifies package, active-formula, or configured-season token drift.
- `422 invalid_request` identifies malformed queries, missing players, duplicates, unknown edit
  targets, or violated bounds.
- `422 invalid_formula` identifies an edit set rejected by the shared formula validator.
- `422 evaluation_failed` identifies a validated temporary formula that cannot evaluate the cohort.

## No-write guarantee

The application reads the package into an immutable baseline at startup. Each preview changes only a
request-local deep copy and is discarded after the response. There is no endpoint for formula files,
reference CSVs, package manifests, presets, or named sessions, and the API never writes to those
paths. Authentication, persistence, deployment, and production hosting remain out of scope.
