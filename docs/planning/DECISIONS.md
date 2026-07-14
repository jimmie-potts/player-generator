# Version 2 decision log

These decisions are approved defaults for the redesign. Create a new dated entry when later work
changes one; do not rewrite history without recording the replacement.

## D-001: Monorepo packages

- **Status:** accepted
- **Decision:** Keep reference building, roster generation, and the web application in one
  repository as independent applications with shared contract and formula packages.
- **Reason:** Shared schemas and calculations require coordinated versioning, while application
  boundaries prevent the current pipeline coupling from returning.

## D-002: Reference and roster terminology

- **Status:** accepted
- **Decision:** Use `reference` for actual-player source data and `roster` for generator output.
  Do not attach an identity qualifier to players, teams, coaches, or rosters.
- **Reason:** Domain data should be handled through the same entity vocabulary regardless of its
  origin.

## D-003: Clean version 2 break

- **Status:** accepted
- **Decision:** Version 2 may replace current commands, paths, and output contracts without a
  compatibility wrapper.
- **Reason:** Compatibility would preserve the coupling and wide-file assumptions that the redesign
  is intended to remove.

## D-004: Local Parquet input

- **Status:** accepted
- **Decision:** Version 2 accepts local Parquet files. Automated remote download is not part of the
  initial reference-data application.
- **Reason:** Local input makes provenance explicit and avoids making ingestion depend on upstream
  availability or redistribution rights.

## D-005: Normalized reference outputs

- **Status:** accepted
- **Decision:** Publish normalized player, season, traditional-stat, advanced-stat, source-ID, and
  provenance CSVs rather than one wide table.
- **Reason:** Stable domain tables isolate source schema drift and allow downstream consumers to load
  only what they need.

## D-006: Player-only roster package

- **Status:** accepted
- **Decision:** The first roster package contains player bio, traditional stats, advanced stats,
  attributes, and a manifest. Team assignment, coaches, and contracts are deferred.
- **Reason:** Those domains require inputs or generation policy not supplied by the initial Parquet
  sources.

## D-007: Adjusted reference templates

- **Status:** accepted
- **Decision:** Generate roster statistics by applying controlled mutations to sampled reference
  player-seasons while preserving consistency between related statistical fields.
- **Reason:** This retains realistic relationships better than independently sampling every metric.

## D-008: Declarative formula controls

- **Status:** accepted
- **Decision:** Store attribute components, weights, direction, eligibility, and rating anchors in a
  validated YAML or JSON document consumed by batch and API paths.
- **Reason:** The UI must be able to preview supported adjustments without parsing or executing
  arbitrary Python.

## D-009: React client with Python API

- **Status:** accepted
- **Decision:** Build a TypeScript React workbench backed by a Python preview API.
- **Reason:** The API keeps one authoritative calculation engine while the client provides a richer
  interactive editing experience.

## D-010: Session-only formula editing

- **Status:** accepted
- **Decision:** The first workbench previews weights, inverse direction, and rating anchors in the
  current session. It may export a proposal but cannot overwrite active configuration.
- **Reason:** This supports safe experimentation before formula governance and persistence are
  designed.

## D-011: Top-player sample with search and pinning

- **Status:** accepted
- **Decision:** Default the workbench to players ranked highest by baseline overall, with search and
  pinning for any reference player.
- **Reason:** Top players expose high-visibility formula effects while search supports targeted
  investigation and specialists.

## D-012: Aggregate player-season grain

- **Status:** accepted
- **Decision:** Contract version 1 uses one aggregate row per player and season across season,
  traditional-stat, and advanced-stat tables. Team identity is optional and present only for a
  single-team aggregate. Team stints are deferred.
- **Reason:** The initial source is already unique by player and year, and treating multi-team labels
  as canonical team IDs would create incorrect joins.

## D-013: Neutral language preserves identity separation

- **Status:** accepted
- **Decision:** Shared player-domain terminology does not change the data boundary. Source names,
  source IDs, and reconciliation mappings remain reference-only, while roster identities are
  generated independently.
- **Reason:** Naming consistency and provenance control solve different problems and both are
  required.

## D-014: One Python distribution with multiple source roots

- **Status:** accepted
- **Decision:** Install the two Python applications and two shared Python packages through one root
  setuptools distribution while keeping their source in separate app and package directories.
- **Reason:** A single clean-install command and shared dependency set simplify contribution without
  weakening the import boundaries enforced by tests.

## D-015: Application-owned configuration

- **Status:** accepted
- **Decision:** Give reference-data and roster-generator separate YAML configuration files containing
  only the settings each current application needs.
- **Reason:** Separate configuration prevents application ownership from being coupled through the
  former root pipeline config while declarative formula configuration remains future work.

## D-016: npm workspace for the workbench

- **Status:** accepted
- **Decision:** Use a root npm workspace with Node.js 22, Vite, React, TypeScript, and Vitest for the
  formula-workbench application.
- **Reason:** npm is available without another package-manager bootstrap, and a committed lockfile
  makes the independently runnable frontend reproducible in CI.

## D-017: Shared evaluator consumer sequencing

- **Status:** accepted
- **Decision:** EPIC-03 publishes the application-independent formula evaluator and migrates the
  current batch compatibility path to it. The preview API remains a US-010 deliverable and must
  import that evaluator when implemented; EPIC-03 does not pull the API forward solely to create a
  second consumer.
- **Reason:** This satisfies the single-evaluator architecture without violating the dependency
  order or expanding declarative-formula work into the later API epic.

## D-018: Published roster possession basis

- **Status:** accepted
- **Decision:** Roster contract version 1 includes `season`, `games`, `minutes`, and `possessions`
  in `player_stats.csv`. Generation infers a template's possession total as the median of its
  available positive total/per-100 pairs, applies the controlled volume mutation once, and derives
  every roster per-100 field from that one published possession value.
- **Reason:** The reference contract publishes per-100 rates but no possession total. One explicit,
  reproducible inference rule preserves cross-stat consistency without adding a separate roster
  season table or independently jittering related rate fields.

## D-019: Roster advanced-stat identities

- **Status:** accepted
- **Decision:** Derive roster `assistRatio` and `estimatedTurnoverPercentage` from mutated event
  operands using the shared play-ending denominator `FGA + 0.44 * FTA + AST + TOV`. Keep
  `reboundPercentage` as a separately mapped, bounded source metric rather than forcing it to equal
  the mean of offensive and defensive rebound percentages.
- **Reason:** The reference adapter maps per-100 rates, assist ratio, estimated turnover percentage,
  and rebound percentage as distinct upstream metrics. Preserving their domain definitions avoids
  silently collapsing separate statistics while still making derived roster values reproducible.

## D-020: Versioned reference player attributes

- **Status:** accepted
- **Decision:** Reference package version 2 adds `player_attributes.csv` at the aggregate
  player-season grain. Every season is evaluated independently through the shared declarative
  engine, and the manifest records the formula version and exact document hash. Version 1 remains
  readable, while new publication defaults to version 2.
- **Reason:** Reference ratings are season-relative derived data. Publishing them with the inputs,
  cohort keys, formula provenance, and package integrity metadata makes the results inspectable and
  reproducible without weakening formula ownership or copying reference identities into roster
  output.

## D-021: Finite turnover-free ratios and shooting-efficiency bounds

- **Status:** accepted
- **Decision:** Derive roster `assistTurnoverRatio` as `AST / max(TOV, 1)` so zero-turnover lines
  remain finite and formula-eligible. Permit roster effective field-goal and true-shooting rates in
  the mathematically valid range 0–1.5.
- **Reason:** Leaving a zero-turnover ratio empty makes otherwise valid generated attributes fail,
  while infinity cannot be represented by the finite-number contract. A one-turnover denominator
  floor preserves the benefit of a turnover-free line. A made three on one attempt yields `1.5`
  effective field-goal and true-shooting rates, so a 0–1 proportion bound rejects valid arithmetic.

## D-022: One generated season per roster player

- **Status:** accepted
- **Decision:** Roster contract version 1 permits exactly one `player_stats.csv` row and one aligned
  `player_advanced_stats.csv` row per `playerId`. `player_attributes.csv` remains at player grain.
- **Reason:** Generation samples one reference player-season for each roster player. Allowing more
  than one generated season would leave the player-grain attribute row unable to identify which
  season it rates, even when the two stat tables share the same multi-season key set.

## D-023: FastAPI preview application with API-owned contracts

- **Status:** accepted
- **Decision:** Implement the formula preview boundary as a FastAPI application served by Uvicorn
  under `apps/formula-workbench/api`. Version 1 HTTP request and response models are API-owned
  Pydantic models and publish their authoritative OpenAPI document from the running application.
  Request JSON accepts only strict camelCase contract fields and their declared scalar types. Run
  CPU-bound preview evaluation from the async route through an application-owned two-worker
  executor rather than blocking other endpoints on the event loop.
- **Reason:** The API needs strict camelCase validation, structured field errors, and a contract that
  the later TypeScript client can inspect without moving transport concerns into the CSV and formula
  contract package. Strict input prevents ambiguous coercion, and the bounded dedicated executor
  preserves responsiveness while avoiding the incompatible FastAPI sync-route/AnyIO and asyncio
  default-executor paths observed on the repository's supported runtime. Keeping the server beside
  the React client preserves one workbench application boundary while the shared Python distribution
  retains a reproducible install and entrypoint.

## D-024: Complete configured preview cohort with bounded responses

- **Status:** accepted
- **Decision:** Load and evaluate one explicitly configured season cohort in memory, rejecting a
  cohort larger than the configured maximum. Calculate baselines and previews over that complete
  fixed cohort, then bound only the top-player response, pins, selected players, and search results.
  Rank overall values with minimum-rank tie semantics and use stable player IDs only to order equal
  values for display. Require each preview request to echo the configured season as a context token.
- **Reason:** Formula priors, percentiles, and rank movement are population-relative. Evaluating only
  the displayed sample would change the calculation, while one season makes stable `playerId`
  selection unambiguous and explicit limits keep local interactive work responsive.
- **2026-07-13 amendment:** Set the exact 1,000-player warm preview budget to 3,000 ms after the
  GitHub Python 3.12 runner measured 2,260 ms against the initial 2,000 ms target. The revised gate
  adds cross-environment operating margin without increasing the cohort or response bounds.
- **2026-07-14 amendment:** Continue evaluating the complete configured cohort for every temporary
  preview rating, component and composite percentile, and overall rank, but materialize temporary
  explanation trees only for the request's selected player IDs. Unselected explanations cannot be
  exposed by the response contract, so constructing them adds work without changing any calculation
  population or result.

## D-025: Shared package integrity with active-formula recalculation

- **Status:** accepted
- **Decision:** Put reusable reference manifest, exact-file-set, hash, row-count, contract, and
  mutation-window checks in `data-contracts`, then let each application apply its own joining and
  compatibility policy. The preview API recalculates its baseline with the active shared-engine
  formula and exposes the package identity, active formula identity, and configured season as context
  tokens. It compares published reference attributes with the recalculation only when their formula
  version and exact document hash match the active formula.
- **Reason:** Applications should not import one another or duplicate integrity rules. Published
  attributes describe the package's calibration snapshot rather than constraining a later consumer's
  selected formula, while explicit identities prevent stale browser requests from mixing package,
  baseline, and formula state.

## D-026: Server-authoritative designer proposals and tiered comparison

- **Status:** accepted
- **Decision:** EPIC-06 edits only existing formula component weights, component directions, rating
  anchors, and the proposed formula version. The preview API returns the exact validated temporary
  formula document and calculates selected-attribute ranks over the same complete cohort as overall
  ranks. The default comparison contains three highest-ranked eligible players from each populated
  talent tier. The reusable representative endpoint accepts one through five per tier, while the
  workbench exposes one through three, leaving capacity for ten session-only pins within the
  25-player preview limit at its 15-player default.
- **Reason:** Returning the validated document avoids reproducing formula-merge behavior in
  TypeScript and makes the exported JSON directly usable by batch consumers. Attribute ranks remain
  population-relative and therefore belong beside the shared evaluator, not in the bounded browser
  sample. Tier-stratified defaults expose tuning effects beyond the top two tiers while explicit
  limits preserve interactive response bounds.

## D-027: Session-scoped client state with cancellable authoritative previews

- **Status:** accepted
- **Decision:** Keep workbench edits, the selected player and attribute, and at most ten pins in
  React memory for the current page session. Load all formula, metric, player, and calculation data
  through a typed `/api/v1` client, verify response context identities before combining data, debounce
  preview requests, abort superseded requests, and clear results that are stale or failed. Client
  validation may provide immediate form feedback but cannot produce ratings. Enable proposal export
  only from the latest successful response and serialize its exact `previewDocument` as formatted
  JSON.
- **Reason:** A local, reversible design loop needs responsive controls without creating a second
  formula engine or an implicit persistence layer. Context verification and cancellation prevent
  asynchronous responses from mixing formula, package, or season state. Exporting the server-owned
  document preserves shared-validator semantics and makes the handoff directly consumable by the
  roster generator without reconstructing merge behavior in TypeScript.
