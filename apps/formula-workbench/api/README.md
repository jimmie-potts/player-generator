# Formula preview API

This Python application is the read-only calculation boundary for the formula workbench. It loads
one integrity-checked version 2 reference package, keeps one configured season cohort in memory, and
uses `player_attribute_engine` for both the cached baseline and every temporary preview. The API does
not read Parquet, import source adapters, or implement rating calculations itself.

US-010 established this boundary, and EPIC-06 adds the representative-player, selected-attribute
rank, and export-document fields used by the React client. The additive HTTP contract below remains
version 1 and is owned by the API's Pydantic models and generated OpenAPI document.

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
  max_selected_players: 25
  max_search_results: 20
  max_cohort_size: 1000
  latency_budget_ms: 3000
```

Startup fails before serving requests when the package, its manifest, exact file set, hashes, row
counts, contracts, relationships, or configured cohort is invalid. The full configured season is
evaluated so shooting priors and percentiles retain their declared population. The 1,000-row bound
applies to that in-memory cohort; the smaller baseline-sample, pin, selected-player, and search
limits bound response work. Configuration may lower the version 1 maxima of 25 baseline players,
25 request pins, 25 selected preview players, 20 search results, and 1,000 cohort rows, but cannot
raise them. Older YAML and direct `PreviewSettings` construction without `max_selected_players`
retain their prior behavior by using `max_pinned_players` as the selected-player limit.

## Version and context tokens

Every successful response contains a `context` object. This example uses the local validation
package; `cohortSize` counts every loaded row for the configured season, not only eligible players:

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
  "cohortSize": 582
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
request. The current workbench uses the unpinned `limit=25` response as its fixed baseline-overall
Top 25 view. The endpoint's `pinnedPlayerId` option remains available to other version 1 clients, but
the workbench does not append those players to another comparison view.

### `GET /api/v1/players/representatives`

Returns deterministic baseline groups across the populated formula talent tiers. `perTier` defaults
to 3 and must be an integer from 1 through 5:

```text
GET /api/v1/players/representatives?perTier=3
```

The response is `{context, perTier, tiers}`. Each tier object contains `tier`, `minimum`, `maximum`,
and `players`. Populated tiers are ordered from the highest configured rating range to the lowest,
and players within each tier are the highest baseline-overall ranks followed by stable `playerId`
tie order. Empty tiers are omitted. Each player uses the same baseline summary contract as
`GET /api/v1/players`, with `pinned: false`. Source IDs and reconciliation mappings are never
exposed.

The endpoint's `1..5` range is a reusable API bound. The current workbench intentionally exposes
only `1..3` in its mutually exclusive Tier sample view. Its default is three representatives per
populated tier; those players are not combined with the Top 25 or Custom list views.

### `GET /api/v1/players/search`

Searches display names and stable reference player IDs within the configured season:

```text
GET /api/v1/players/search?q=duren&limit=10
```

Search normalizes text with Unicode NFKC, case folding, and removal of non-alphanumeric characters,
then performs a partial match. Exact IDs and name prefixes sort before other matches, followed by
baseline rank and stable name/ID order. `q` must contain searchable text, and `limit` is `1..20`.
Source IDs and reconciliation mappings are never exposed. The workbench uses these results to build
a session-only Custom list of at most 25 unique players.

### `GET /api/v1/players/{playerId}`

Returns the player's baseline row and the authoritative shared-engine calculation detail: eligibility
and reasons, cohort values and size, raw inputs, metric derivations, component percentiles,
normalized weights, contributions, composite, composite percentile, and final rating. The player
must exist in the configured season cohort.

### `POST /api/v1/previews`

Evaluates a temporary deep copy of the active formula over the same complete season cohort and
returns results only for the selected players. Ratings, component and composite percentiles, and
overall ranks still use every player in that cohort. A request has this shape:

```json
{
  "apiVersion": "1",
  "referencePackageHash": "<context.referencePackage.contentHash>",
  "formulaVersion": "<context.formula.formulaVersion>",
  "formulaDocumentHash": "<context.formula.documentHash>",
  "season": 2026,
  "selectedPlayerIds": ["player-001"],
  "selectedAttribute": "overall",
  "adjustments": {
    "formulaVersion": "1.0.0-proposal.1",
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

The workbench's Tier sample, Top 25, and Custom list views are mutually exclusive clients of this
bound: a preview sends only the active view's IDs, never a union of hidden views. This selection
changes which detailed player results appear in the response, not the population used to calculate
them.

`selectedAttribute` is optional and defaults to `overall` for backward compatibility. It must name
an existing formula attribute. The API ranks its baseline and preview values across the complete
fixed cohort with the same minimum-rank tie semantics used for overall.

`adjustments.formulaVersion` optionally replaces the temporary document's formula version. It is
validated with the rest of the merged formula and changes only the request-local proposal. This
lets an exported proposal carry an explicit version without changing the active formula identity
tokens echoed at the top level of the request.

A rating-scale adjustment replaces the complete anchor list for a named scale. It is deliberately
scale-wide: every attribute that references the scale observes the temporary anchors. Anchors must
remain strictly ordered, span percentiles 0 and 1, map monotonically within 25–99, and satisfy the
shared formula contract. Eligibility, cohorts, metric expressions, output fields, talent tiers, and
active formula configuration are not editable endpoints.

The response includes the active `context`, a `previewFormulaHash`, the exact server-validated
`previewDocument`, warm evaluation time, and each selected player's baseline and preview rows. The
preview document is a deep copy of the merged formula accepted by the shared validator and is
suitable for saving as JSON and passing directly to `roster-generator generate --formula`; returning
it does not write it anywhere. `changes` records the baseline value, preview value, and numeric delta
for every rating output. Baseline and preview calculation details contain the raw inputs,
percentiles, normalized weights, and contributions.

The existing `baselineRank`, `previewRank`, and `rankMovement` fields describe overall. Each player
also has `attributeRank` with `attribute`, `baselineRank`, `previewRank`, and `rankMovement` for the
requested `selectedAttribute`. All ranks are calculated over the same full cohort; positive movement
means the player moved toward rank 1.

Temporary preview explanation trees are materialized only for `selectedPlayerIds`. This changes no
rating, percentile, or rank population: the full cohort is still calculated before the response is
selected. It avoids building nested raw-input, metric-detail, percentile, weight, and contribution
objects for players the response contract cannot expose. Cached baseline explanations remain
available to the player-detail endpoint.

The approved warm calculation budget is 3,000 ms for a configured cohort of at most 1,000 players.
It measures the in-process shared-engine recalculation and excludes package loading and server
startup. The async preview handler explicitly dispatches its CPU-bound evaluation to an
application-owned executor with two bounded workers. Formula, metric, baseline, representative,
search, and detail requests can therefore continue on the event loop while recalculation runs in a
worker thread.

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
request-local deep copy and is discarded after the response. `previewDocument` enables a browser to
offer an explicit client-side download, but there is no server endpoint that writes formula files,
reference CSVs, package manifests, presets, or named sessions, and the API never writes to those
paths. Authentication, persistence, deployment, and production hosting remain out of scope.
