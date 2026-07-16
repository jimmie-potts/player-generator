# Decision log

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

## D-003: Clean redesign break

- **Status:** accepted; superseded by [D-035](#d-035-current-version-1-package-inventory)
- **Decision:** The repository redesign may replace the commands, paths, and output contracts that
  predated the application split without retaining wrapper interfaces.
- **Reason:** Retaining superseded wrapper interfaces would preserve the coupling and wide-file
  assumptions that the redesign is intended to remove.

## D-004: Local Parquet input

- **Status:** accepted
- **Decision:** The normalized reference-data application accepts local Parquet files. Automated
  remote download is not part of its publication path.
- **Reason:** Local input makes provenance explicit and avoids making ingestion depend on upstream
  availability or redistribution rights.

## D-005: Normalized reference outputs

- **Status:** accepted; superseded by [D-035](#d-035-current-version-1-package-inventory)
- **Decision:** Publish normalized player, season, traditional-stat, advanced-stat, source-ID, and
  provenance CSVs rather than one wide table.
- **Reason:** Stable domain tables isolate source schema drift and allow downstream consumers to load
  only what they need.

## D-006: Player-only roster package

- **Status:** accepted; amended by [D-035](#d-035-current-version-1-package-inventory)
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

- **Status:** accepted; amended by [D-035](#d-035-current-version-1-package-inventory)
- **Decision:** Contract version 1 uses one aggregate `player_stats.csv` row per player and season,
  containing season context and traditional, rate, and advanced observations. The roster profile
  additionally requires an explicit `possessions` total; the reference profile publishes per-100
  rates but no possession total. Team identity is optional and present only for a single-team
  aggregate. Team stints are deferred.
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
- **Decision:** EPIC-03 publishes the application-independent formula evaluator and moves the
  standalone batch path to it. The preview API remains a US-010 deliverable and must
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

## D-020: Reference player attributes

- **Status:** accepted; amended by [D-035](#d-035-current-version-1-package-inventory)
- **Decision:** Publish `player_attributes.csv` at the aggregate player-season grain. Every season is
  evaluated independently through the shared declarative engine, and the manifest records the
  formula version and exact document hash. D-035 incorporates this output into the current version 1
  reference profile.
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

- **Status:** accepted; amended by [D-035](#d-035-current-version-1-package-inventory)
- **Decision:** The version 1 roster profile permits exactly one `player_stats.csv` row per
  `playerId`. `player_attributes.csv` remains at player grain.
- **Reason:** Generation samples one reference player-season for each roster player. Allowing more
  than one generated season would leave the player-grain attribute row unable to identify which
  season it rates.

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
  input-requirement policy. The preview API recalculates its baseline with the active shared-engine
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

## D-028: Accessible exact-allocation editing and persistent explanation

- **Status:** accepted
- **Decision:** Present every selected attribute's components as native range sliders in integer
  one-percentage-point units, accompanied by one non-editing stacked allocation bar. Changing a
  component assigns its requested percentage and distributes the remaining units proportionally
  across its peers. Floor each proportional share, award remaining units by largest fractional
  remainder, and resolve equal remainders by formula document order. When every current peer share
  is zero, use baseline proportions and then equal shares as deterministic fallbacks. Normalize an
  untouched positive-sum source allocation for slider and allocation-bar presentation without
  rewriting the loaded formula; after the designer changes any component, make the authored
  allocation total exactly `1.00`. Keep a sole component fixed at 100%. On desktop, give Formula and
  Authoritative Explanation equal viewport-bounded panes, let Formula scroll independently, and
  keep the rating summary visible while secondary explanation details use native expandable
  sections. Return to normal document flow on narrow layouts. Supply native expandable section
  guidance and a glossary containing stable terms plus a catalog derived from loaded formula and
  metric metadata.
- **Reason:** Native sliders provide familiar keyboard and assistive-technology behavior, while the
  stacked bar communicates the full allocation without the ambiguous interaction model of a custom
  multi-thumb control. Deterministic integer redistribution makes the designer's percentages
  explicit and prevents one edit from producing an allocation above or below 100%. Persistent
  results shorten the edit-and-compare loop, responsive normal flow avoids trapping mobile content,
  and model-derived glossary entries remain current without reimplementing formula behavior. The
  API still validates every proposal and the shared Python engine remains the only rating evaluator.

## D-029: Mutually exclusive comparison sets over one fixed cohort

- **Status:** accepted
- **Decision:** Offer three mutually exclusive Player Comparison views. `Tier sample` remains the
  default and shows one through three highest baseline-overall players from each populated talent
  tier. `Top 25` shows the 25 players returned in baseline-overall order by
  `GET /api/v1/players?limit=25`; its membership and order do not reshuffle after a temporary edit.
  `Custom list` lets the designer search the configured reference cohort and keep up to 25 unique
  players in React memory for the page session. Send only the active view's player IDs to a preview,
  never a union of multiple views and never more than the API's 25-player detail bound. When a
  formula has enough populated tiers for the selected per-tier count to exceed that bound, block the
  tier preview with a recovery message rather than sending an invalid or silently truncated set.
  The selected view bounds which detailed player results the API returns, but it does not define the
  statistical population: the preview API and shared Python engine continue to calculate ratings,
  percentiles, and ranks over the complete fixed season cohort. Preserve each view's selected player
  while switching views when that player remains in the view.
- **Supersedes:** [D-011](#d-011-top-player-sample-with-search-and-pinning) and the
  comparison-composition portion of
  [D-026](#d-026-server-authoritative-designer-proposals-and-tiered-comparison) that combines the
  15-player tier default with ten pins, plus the ten-pin limit in
  [D-027](#d-027-session-scoped-client-state-with-cancellable-authoritative-previews). D-026's
  server-authoritative proposal and complete-cohort rank decisions and D-027's session-only,
  context-checked, cancellable preview decisions remain in force. The lower-level API's bounded
  `pinnedPlayerId` query remains part of its version 1 contract but is no longer the workbench's
  comparison-composition model.
- **Reason:** Separate views let a designer choose broad curve coverage, an elite baseline scan, or
  a targeted investigation without an ambiguous combined table or a hidden capacity tradeoff.
  Fixed baseline membership makes before-and-after Top 25 impact comparable, and a 25-player custom
  ceiling uses the preview contract's existing response bound. Keeping the full cohort authoritative
  prevents ratings and ranks from changing merely because the designer switches which rows are
  visible.

## D-030: Formula preview version 1 bounds are contract maxima

- **Status:** accepted
- **Decision:** Treat 25 baseline players, 25 request pins, 25 selected preview players, 20 search
  results, and 1,000 cohort rows as hard maxima of the version 1 HTTP contract. Local configuration
  may lower but cannot raise those limits. Configure selected preview players separately from request
  pins; existing configuration that omits the selected-player setting inherits its pin limit so the
  alignment does not broaden its prior preview behavior.
- **Reason:** Response and cohort bounds protect the API's validated latency and payload contract.
  Allowing alternate configuration to exceed them makes one API version expose different limits,
  while reusing the pin setting for preview selection conflates independent endpoint concepts.

## D-031: Season-ending-year convention

- **Status:** accepted
- **Decision:** Interpret every integer `season` in the reference and roster player-data contracts
  as the calendar year in which that basketball season ends. For example, `2025` identifies the
  2024-25 season and `2026` identifies the 2025-26 season. A roster row's season is the sampled
  statistical basis for that generated player; it is not a package-wide league-starting season and
  may differ between players in one roster package.
- **Reason:** A single integer is deterministic and already used throughout reference selection,
  roster generation, formula evaluation, and package validation. Defining its direction removes the
  ambiguity that would otherwise make cross-project conversion to NBA-GM's `YYYY-YY` season keys
  error-prone.

## D-032: Consolidated NBA-GM MVP roster handoff

- **Status:** accepted; amended by [D-034](#d-034-player-data-contract-version-1-baseline) and
  [D-035](#d-035-current-version-1-package-inventory)
- **Decision:** Target NBA-GM's MVP build-time handoff as one manifest-backed, player-only package
  containing `players.csv`, a consolidated `player_stats.csv`, and `player_attributes.csv`.
  Consolidate every currently published roster traditional, rate, possession, and advanced metric
  into the one statistics row for each player. Keep attributes at player grain as separately
  versioned formula output. Preserve exact player-key equality across all CSVs. Retain a contract
  identifier for reproducibility. Any generated review workbook remains outside the canonical
  package and is values-only and nonauthoritative.
- **Scope boundary:** NBA-GM consumes roster statistics as MVP simulation inputs and owns league
  context, positions, assignments, contracts, detailed ratings, tendencies, and other
  simulation-specific transformations. ESPN-derived simulation statistics, deeper metrics, and
  personality traits or descriptions require later stories and do not add placeholders to the MVP
  contract. D-033 and D-034 subsequently established the corresponding reference-profile boundary.
- **Implementation note:** US-017 applies the consolidated baseline to both publishers. D-022's one
  generated statistical season per roster player and player-grain attribute rules remain in force.
  D-006's player-only domain boundary also remains in force.
- **Reason:** Traditional, rate, possession, and advanced observations have the same lifecycle and
  player key. One consolidated statistics table avoids a compulsory consumer join without weakening
  semantic validation, while a shared schema and synthetic fixture let player-generator and NBA-GM
  implement the handoff independently.

## D-033: Reference and roster player-file parity

- **Status:** accepted; amended by [D-034](#d-034-player-data-contract-version-1-baseline) and
  [D-035](#d-035-current-version-1-package-inventory), and clarified by
  [D-038](#d-038-version-1-age-and-package-scoped-player-identity)
- **Decision:** Maintain the corresponding reference and roster `players.csv`, `player_stats.csv`,
  and `player_attributes.csv` surfaces as two profiles of one player-data contract. Shared columns
  must retain the same name, relative order, scalar representation, semantic meaning, unit or scale,
  bounds or enum, derivation classification, season convention, and serialization in both profiles.
  Any shared field addition, removal, rename, or formatting change must update both profiles and
  their schemas, fixtures, validators, tests, and documentation in the same story and pull request.
  New player-content fields default to both profiles; a one-profile field requires a dated decision
  and an explicit extension declaration. Cross-profile contract tests must fail when shared
  definitions drift. As part of EPIC-08, consolidate traditional and advanced statistics into
  `player_stats.csv` in both published profiles.
- **Profile boundaries:** Parity does not require equal row values, IDs, grains, or complete package
  inventories. Reference-only season context, source IDs, provenance, reconciliation, and audit data
  remain behind the reference boundary. Roster-only deterministic generation inputs and manifest
  metadata remain in the roster profile. Profile-specific key prefixes, availability-based null
  overrides, and other extensions must be closed and explicitly declared; they must not redefine a
  shared field's type, meaning, unit, bounds, or derivation. NBA-GM continues to consume only the
  player-only roster profile.
- **Supersedes:** This decision supersedes D-032's planned reference-package exception. D-035 fixes
  the current version 1 inventories. D-006's player-only roster scope and the prohibition on
  publishing source identities in roster data remain in force.
- **Reason:** Reference data is the calibrated counterpart of roster data. Allowing their common
  player surfaces to evolve independently would duplicate contract work and invite semantic drift
  before NBA-GM integration and later enrichment. Shared definitions and synchronized delivery keep
  both outputs reviewable and compatible without weakening their provenance boundary.

## D-034: Player data contract version 1 baseline

- **Status:** accepted; amended by [D-035](#d-035-current-version-1-package-inventory)
- **Decision:** Establish the parity-aligned player-data format as contract version 1 and the
  baseline for player-generator and NBA-GM integration. The contract is one family with `reference`
  and `roster` profiles. Corresponding `players.csv`, consolidated `player_stats.csv`, and
  `player_attributes.csv` content derives from shared definitions with declared profile
  extensions. NBA-GM consumes only the player-only roster profile. Contract version, profile,
  package, manifest, adapter, and formula identities remain distinct version domains.
- **Delivery:** [US-016](user-stories/US-016-nba-gm-mvp-roster-contract.md) governs the
  machine-readable version 1 schemas and paired synthetic fixtures. US-017 applies the profiles to
  both publishers and their supported readers. Both stories remain in progress until final
  validation and completion evidence are recorded.
- **Amends:** D-032 and D-033 remain the accepted decision history that established the consolidated
  roster shape and reference/roster parity. This decision replaces their transitional framing with
  one version 1 baseline while retaining their ownership, identity-boundary, deterministic
  publication, consolidated-statistics, and parity requirements.
- **Reason:** NBA-GM integration begins with this format. Treating internal package history as
  cross-project contract history would imply support obligations that the two projects never
  established and would obscure the one interface they are now implementing in parallel.

## D-035: Current version 1 package inventory

- **Status:** accepted
- **Accepted:** 2026-07-15
- **Decision:** Player data contract version 1 is the only normalized package contract. Its
  reference profile contains `players.csv`, `player_stats.csv`, `player_attributes.csv`,
  `player_source_ids.csv`, `sources.csv`, `audit.json`, and `manifest.json`. Its roster profile
  contains `players.csv`, `player_stats.csv`, `player_attributes.csv`, and `manifest.json`. Season
  context and traditional, rate, and advanced observations are governed columns in each profile's
  `player_stats.csv`. The roster profile additionally requires explicit `possessions`; the reference
  profile publishes per-100 rates but no possession total. Exact-file validation rejects every
  undeclared package entry.
- **Amends:** This decision gives D-034 its exact current inventory and replaces D-003's transitional
  numbering, D-005's split reference surfaces, D-020's additive package framing, and D-022's split
  roster-stat surface. Their provenance, identity, formula, single-season, determinism, and atomic
  publication requirements remain in force.
- **Reason:** NBA-GM integration starts with this format, and no external consumer depends on another
  normalized layout. One current contract and one statistics surface per profile avoid ambiguous
  package histories and unnecessary joins.

## D-036: Shared physical measurement representation

- **Status:** accepted
- **Accepted:** 2026-07-15
- **Decision:** Define shared `heightInches` and `weightPounds` fields as finite numbers bounded to
  60–96 inches and 140–400 pounds. Preserve available fractional reference precision and values
  within the governed reference domain. Generated roster values may remain whole numbers because
  every integer is valid under the shared number representation. Do not round, truncate, or
  fabricate a physical value merely to align profiles.
- **Delivery:** US-016 records the shared scalar definition and exact temporary profile differences;
  US-017 applies it to both expanded runtime schemas and publishers. NBA-GM consumes the roster
  values as numbers and must not assume the lexical representation proves an integer-only contract.
- **Reason:** The reference contract already accepts legitimate fractional measurements, including
  synthetic conformance coverage, and its valid domain extends beyond the roster schema's current
  350-pound ceiling. Choosing the narrower roster representation would either reject valid reference
  data or require an unapproved lossy normalization rule. The shared number and domain bounds
  preserve source values while remaining backward-compatible with generated whole-unit values.

## D-037: Lossless shared advanced-metric bounds

- **Status:** accepted
- **Accepted:** 2026-07-15
- **Decision:** Give shared offensive and defensive ratings a nonnegative floor but no artificial
  upper ceiling. Treat their signed net ratings and `playerImpactEstimate` as unbounded finite
  values; `playerImpactEstimate` is a dimensionless index rather than a 0–1 proportion. A publisher
  may emit a narrower subset, but a profile extension must not narrow the shared schema or discard an
  otherwise valid reference row.
- **Delivery:** US-016 records the shared bounds and exact temporary differences from both runtime
  schemas. US-017 aligns the expanded schemas and publishers. Existing roster mutation clamps may
  continue to keep generated values in a narrower operating range because that does not change the
  accepted field domain.
- **Reason:** The current reference corpus contains legitimate finite observations outside the
  roster schema's earlier 0–200 rating, -200–200 net-rating, and 0–1 impact limits, especially in
  small samples. No stable domain formula supplies a defensible replacement ceiling. Retaining the
  observations is lossless and keeps reference calibration data authoritative; silent filtering or
  clamping would change the source population and formula cohorts.

## D-038: Version 1 age and package-scoped player identity

- **Status:** accepted
- **Accepted:** 2026-07-15
- **Decision:** Keep optional integer `age` as the version 1 roster player's basic age snapshot and
  do not add `birthDate` to the roster profile. NBA-GM should preserve an unknown birth date when its
  model permits it. If an NBA-GM-owned boundary requires a non-null date, NBA-GM may apply one
  configured global default; the value remains a consumer default, is never derived from `age`, and
  must not be represented as observed player data.
- **Identifier rule:** Keep the existing deterministic `player_[0-9a-f]{16}` value as an opaque key
  unique within one roster package. NBA-GM preserves that `playerId` verbatim and scopes persistence
  uniqueness to its save. When source-package provenance or cross-package distinction is needed,
  `(manifest.contentHash, playerId)` is the stable import identity. Separate packages may therefore
  reuse a `playerId` without collision; no rewritten ID, global UUID namespace, crosswalk, or new
  manifest namespace is required.
- **Future teams and coaches:** `teamId` and `coachId` will be stable opaque nonempty strings unique
  within their NBA-GM-owned league context and joined by exact string equality. Their population and
  any concrete generation convention remain future work under US-014.
- **Delivery:** US-016 records these semantics in the version 1 family contract and NBA-GM handoff.
  US-017 preserves the existing roster IDs and manifest content identity while aligning publication;
  it does not introduce a separate namespace mechanism.
- **Reason:** NBA-GM stores entities under a save boundary and the roster manifest already identifies
  the exact package bytes. Reusing those two existing scopes is deterministic and collision-safe for
  the handoff without adding identity machinery. Keeping age as the source fact also avoids inventing
  a precision the producer does not possess.

## D-039: Relationship identity and membership semantics

- **Status:** accepted
- **Accepted:** 2026-07-16
- **Decision:** A `foreignKey` must target exactly one declared unique key, in the declared column
  order. Its source and target have equal arity and scalar types, its source fields are required and
  non-nullable, and every source tuple resolves. Use `valueExists` for the same typed, required
  source-to-target membership check when the target columns do not identify one row. Classify
  `player_source_ids.sourceType -> sources.sourceType` as `valueExists`; multiple registered inputs
  may legitimately use the same source type while `sourceId` remains the source-row key.
- **Validation:** Validate unique-key and relationship declarations against contracted columns
  independently of row presence. Empty tables therefore cannot hide an empty, duplicate, unknown,
  nullable, or non-key declaration. Keep exact-key-set validation separate because it compares
  complete key populations rather than one-way references.
- **Reason:** Treating every membership rule as a foreign key either permits ambiguous row identity
  or forces a false uniqueness constraint. Naming the two semantics explicitly keeps relational
  guarantees honest without preventing multiple registered files from sharing one adapter type.
