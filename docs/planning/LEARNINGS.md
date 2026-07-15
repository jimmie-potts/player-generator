# Learning log

This is an append-oriented record of reusable facts discovered while planning or implementing the
redesign. Each completed story must add any relevant findings here and retain detailed evidence in
its completion notes.

## Planning baseline — 2026-07-12

- The current implementation is a single Python package in which ingestion, formulas, roster
  generation, comparison, and CLI orchestration directly import one another.
- Current rating formulas are Python dictionaries in `ratings.py`; weights and inputs cannot be
  edited safely by a browser without first extracting a declarative contract.
- The current source manifest downloads one pinned `playerstats.parquet` URL. Version 2 local-file
  ingestion is a behavior change, not just a new command name.
- The current processed model uses wide player-season and latest-season CSVs. Moving to normalized
  contracts requires explicit keys, join validation, and provenance tables.
- The current generator emits a combined roster JSON and a flattened player CSV. Version 2 instead
  publishes a player-only package split by concern.
- Current team definitions and assignments exist, but first-release version 2 team output is
  deliberately out of scope.
- The upstream `llimllib/nba_data` snapshot has no observed root license. Raw and transformed named
  reference data should remain local and untracked unless redistribution rights are established.
- ESPN play-style data can improve future attributes, but source-ID reconciliation and schema
  differences make it a separate adapter and formula-extension story.

### 2026-07-12 — US-001

- Setuptools can discover packages across multiple app and package source roots while exposing one
  root editable install and separate console entrypoints.
- Physical directories alone do not enforce application separation; AST import tests make the
  reference-to-roster prohibition executable.
- The current processed player-season CSV is only a transitional application seam. It is not the
  versioned normalized reference package planned by US-005 and US-008.
- A static React shell is sufficient to prove the frontend build, test, and runtime boundary without
  pulling formula or API behavior forward from later epics.
- Root aggregate commands must include source acquisition or verification so they work from a clean
  checkout, even when lower-level build commands intentionally fail fast on missing inputs.
- Declared runtime engine ranges should match the strictest locked build-tool requirement; Vite 7
  requires Node.js 22.12 or newer within the Node 22 line.

### 2026-07-12 — US-002

- Output terminology appears in paths, code identifiers, report JSON keys, CSV headers, schemas,
  fixtures, and documentation; all of those surfaces must move together.
- Generated examples and reports should be rebuilt from their owning applications after interface
  renames rather than edited by hand.

### 2026-07-13 — US-003

- Parquet metadata does not identify the application adapter schema version; local registration
  must pair each file with an explicit source type and adapter version.
- Idempotent registration must preserve its first processing timestamp as well as its content hash,
  otherwise unchanged inputs would make later package provenance non-deterministic.
- Registration can remain safe for named third-party data by storing only an ignored local path and
  provenance record; the application never needs to copy source bytes into its workspace.
- A conservative adapter may require only observed stable fields and leave other source-specific
  values unavailable rather than treating a guessed upstream schema as a supported contract.

### 2026-07-13 — US-004

- Source IDs must remain namespaced by source type; equal-looking values from different providers
  are not identity evidence. Reviewed overrides and unique normalized exact names are separate,
  auditable reconciliation rules.
- `team_count` is unavailable in older NBA rows. Canonical team identity is safe only when that
  field explicitly equals one; last-team and aggregate source labels remain audit context.
- Repeated seasons can disagree on bio values such as height or weight. Declared source precedence
  still needs a deterministic within-source rule, and latest season followed by source ID provides
  one while preserving every distinct candidate in the conflict audit.
- Adapters should map only fields whose units and meaning are explicit. Ignoring ambiguous ESPN
  height and weight columns avoids silently converting an unknown upstream contract.
- Parquet logical date and timestamp columns can surface as Python dates or pandas timestamps.
  Date-valued adapter fields need field-specific normalization to `YYYY-MM-DD` instead of generic
  scalar serialization that retains a time component.
- Optional numeric source fields can encode missing values as blank text. Treat blanks as null only
  where the adapter already permits numeric text, and keep required-field wrappers responsible for
  rejecting the resulting missing player IDs or seasons.
- Opaque player IDs anchored to a primary namespaced identity remain stable when a supplemental
  source is later reconciled, while opaque player-season IDs make aggregate grain executable.

### 2026-07-13 — US-005

- A machine-readable CSV contract must govern ordered headers as well as field types and keys;
  validating row mappings alone cannot detect a consumer-visible header reorder.
- Validate the serialized staging directory before publication. This catches encoding, empty-cell,
  numeric-format, and header errors that in-memory canonical validation cannot observe.
- A deterministic package content hash can cover contract CSVs and audit while excluding the
  manifest's `createdAt`; persisted registration timestamps keep provenance stable between builds.
- Directory-level publication needs a same-parent staging directory and backup restoration so a
  failed final rename cannot leave a partial package or destroy the last valid one.
- A registry path is mutable even when its stored provenance is deterministic. Publication must
  revalidate registered hashes and row counts before consuming a file and recheck after reading;
  atomic output replacement alone cannot prevent stale input metadata from reaching a package.
- Real source files may encode unavailable optional text as whitespace. Normalize it to null before
  CSV writing so the contract produces an empty cell rather than invalid non-empty text.

### 2026-07-13 — US-006

- A formula document needs both a structural versioned schema and semantic validation of metric
  dependencies, weights, directions, cohort references, and output coverage. A JSON shape alone
  cannot reject a cyclic derived metric or an unknown component.
- Derived metric policy is formula behavior. Shooting priors and season schedules must travel with
  the formula version instead of remaining in application configuration, or identical source rows
  can produce different ratings without a formula-version change.
- Shooting stabilization must use the full season before minimum-sample eligibility is applied to
  preserve the declared league prior. Eligibility applies to ranking and rating, not to construction
  of that prior.
- Existing percentile semantics are calibration behavior: average ties with pandas rank-percentile
  semantics gives an eligible singleton `1.0`. Encoding this rule prevents a refactor from silently
  shifting every anchor mapping.
- A shared engine stays reusable when it accepts joined in-memory rows and returns ordered output
  plus JSON-serializable explanations. Package loading, source adapters, and application
  configuration remain consumer responsibilities.
- Individually finite weights still need overflow-safe normalization. Scaling by the largest weight
  before summing preserves a normalized total of 1 even near floating-point limits.
- Formula evaluation must read input aliases from an immutable source snapshot and make implicit
  derivation dependencies explicit. Otherwise harmless document-key reordering or a derived season
  metric can move validation failures from load time to runtime.

### 2026-07-13 — US-007

- A rank-only synthetic cohort can preserve named calibration expectations without committing
  source IDs or third-party reference rows. Cohort size and ordinal rank are sufficient to lock the
  impact percentile, overall-anchor mapping, and tier.
- Explanation regressions should reconstruct formula-derived metrics before reconstructing
  weighted contributions. Otherwise a shooting prior, ratio zero policy, or scheduled-game rule
  could drift while contribution arithmetic still appears correct.
- Season-relative overall ratings need cohort and availability context. A small availability weight
  can visibly separate otherwise prominent players when their availability percentile ranks differ
  sharply.
- Representative snapshots should include a specialist and independently missing attributes, not
  only uniformly high and low players. The core evaluator preserves valid per-attribute results;
  the current legacy wide adapter deliberately keeps only complete rating vectors.

### 2026-07-13 — US-008

- A normalized CSV contract is not a complete package-integrity contract. Consumers must also
  verify the package manifest, exact file set, per-file hashes and row counts, aggregate content
  hash, and compatible formula reference-contract version before using validated rows.
- A published package path can change after its first hash check. Rechecking every manifest file
  after typed reads closes the consumer-side mutation window before template selection.
- Formula-derived priors and percentiles require the whole configured season cohort. Evaluate that
  cohort before applying generator-specific games and minutes filters, then sample only complete
  outputs with explicit recency and minutes weights.
- Formula completeness does not prove that a row has the primitive shooting, event, and
  total/per-100 inputs required for controlled mutation. Apply generation-viability checks before
  weighted sampling so unsupported templates cannot fail only for particular seeds.
- An exact package boundary must compare every directory entry, not only regular files; otherwise
  an unmanifested source-data directory can bypass the file-set check.
- Formula compatibility must cover the inputs available to every evaluation stage. A formula can
  be valid against reference data and still be unusable after roster mutation if it requires a
  season or provenance field that is absent from the generated evaluation frame.

### 2026-07-13 — US-009

- The player-only roster package still needs `season`, `games`, and `minutes` beside traditional
  stats because the formula engine evaluates season cohorts and enforces availability thresholds.
- Reference per-100 rates do not expose a possession total. Infer one deterministic template basis,
  mutate it once with volume, publish it, and derive all roster per-100 values from it instead of
  allowing each rate to drift independently.
- Generate attributes after statistics mutation. Direct rating mutation bypasses formula
  governance and can make published attributes impossible to reproduce from the roster package.
- Validate native mappings, serialized CSVs, semantic statistical identities, integrity metadata,
  and identity leakage before atomic replacement. Each layer catches a different partial-package or
  cross-domain failure mode.
- A deterministic manifest should omit wall-clock creation time and separately pin reference
  content, exact formula bytes, semantic configuration, seed, individual files, and aggregate
  content.
- Similar metric names do not imply interchangeable formulas. Assist ratio and estimated turnover
  percentage use a play-ending denominator rather than the roster possession total, while rebound
  percentage remains distinct from its offensive and defensive components.
- Derived shooting efficiencies are not ordinary 0–1 proportions: a made three on one attempt
  yields `1.5` effective field-goal percentage. Contract bounds must reflect the arithmetic that
  semantic validation recomputes.
- A zero-turnover assist ratio cannot be published as infinity, but leaving it empty makes an
  otherwise valid generated player formula-ineligible. Use the explicit finite denominator floor
  `max(turnovers, 1)` in both generation and semantic validation.
- Parse and hash a custom formula from the same immutable byte snapshot. Reading the path again
  after generation can make the manifest describe bytes that were not used for evaluation.
- Exact key-set validation removes duplicates before comparing sets. When a related table has a
  coarser grain, enforce uniqueness at that projection too; otherwise multiple stat seasons can
  collapse to one `playerId` and appear compatible with a player-grain attribute table.

### 2026-07-13 — US-015

- Adding a deterministic derived CSV to a package with an exact-file-set contract requires a new
  package and contract version even when every existing input header remains unchanged. Preserve
  the older schema explicitly when downstream readers still need to consume prior packages.
- Season-relative ratings must evaluate each complete season cohort before attaching
  `playerSeasonId` to the ordered results. Verify evaluator row identity before enrichment so a
  reordered result cannot silently assign one player's ratings to another player-season.
- A reference package's formula metadata describes its published calibration snapshot, not a
  mandatory formula for later roster generation. Validate and hash the published attributes, but
  recompute roster selection and output when the consumer requests a different formula document.
- Historical source seasons can predate a formula's explicit schedule. Preserve their contracted
  attribute rows with empty calculations instead of broad-catching evaluator failures or silently
  inventing schedule policy; other evaluation errors must still fail publication.

### 2026-07-13 — US-010

- Interactive response bounds must not become calculation-population bounds. Formula priors,
  percentiles, and rank movement remain correct only when baseline and preview evaluate the same
  complete configured season cohort before selecting response rows.
- A published attribute table is a useful parity oracle only when its formula version and exact
  document hash match the active evaluator input. Otherwise its provenance remains valid package
  context, while the consumer must label and recalculate its own active baseline.
- Reference-package integrity is consumer-independent, but joining, formula compatibility, identity
  exposure, and selection policy are application concerns. Sharing the former prevents duplicated
  mutation-window checks without coupling applications through one consumer's policy.
- Package and active-formula hashes plus the configured season are practical optimistic context
  tokens for a stateless preview API. Rejecting stale tokens before recalculation prevents a client
  from presenting results against a package, formula, or cohort baseline it did not request.
- Strict transport models should reject field aliases and scalar coercion even when internal Python
  models use snake_case names. One published camelCase shape keeps browser behavior and structured
  field errors deterministic.
- Calling shared-engine Pandas evaluation directly from an async FastAPI handler would block the
  event loop. The sync-route/AnyIO threadpool path hung under the repository's Python 3.14 and current
  Starlette/httpx2 stack, and the runtime's asyncio default executor also hung in isolation. An
  application-owned bounded executor kept lightweight inspection and search endpoints responsive
  during recalculation.
- A performance acceptance gate needs margin across supported runners, not only a developer
  workstation. Preserve the workload and data bounds, record the observed slower environment, and
  revise the documented budget explicitly when the original target is not portable.

### 2026-07-14 — US-010 review optimization

- Calculation population and explanation materialization are separate concerns. A preview must
  evaluate the complete fixed cohort for ratings, percentiles, and ranks, but it can build nested
  explanation trees only for selected player IDs when the response contract cannot expose any other
  player's explanation.
- Selective explanation materialization is safe only when it does not filter metric preparation,
  eligibility, percentile cohorts, composites, ratings, or rank inputs. Tests should prove full-cohort
  result parity as well as the absence of unselected temporary explanations.
- Type annotations do not protect a shared Python API at runtime. Optional public filters should
  validate both their collection shape and every element, then report malformed values through the
  package's domain error instead of leaking `TypeError`.

### 2026-07-14 — US-011

- The browser can explain a formula without duplicating its evaluator when the API exposes both
  declarative metadata and the shared engine's calculation tree. Treat unsupported attributes,
  missing inputs, and eligibility exclusions as different states because each calls for a different
  design response.
- Cross-endpoint context checks belong in the typed client boundary. Combining individually valid
  responses without comparing API, package, formula, season, and cohort identities can produce a
  plausible but internally inconsistent inspection view.
- A dense formula can scroll independently without hiding its result when the explanation pane has
  the same bounded desktop height and keeps its score summary sticky. Remove those nested scroll and
  sticky constraints when panes stack so narrow screens retain natural reading order.
- Native `details` elements provide keyboard-accessible progressive disclosure for generous help
  and calculation traces. A glossary can combine curated domain language with a catalog derived
  from API formula and metric metadata without becoming a second source of formula behavior.

### 2026-07-14 — US-012

- Client-side validation improves editing feedback but cannot define formula validity. Send only
  supported adjustments to the API, clear failed or superseded results, and display only the latest
  server-authoritative preview.
- A proposal export should use the exact fully merged document returned after server validation.
  Reconstructing it from client deltas can miss shared rating-scale effects, contract fields, or
  future contract defaults even when the visible preview is correct.
- Request cancellation is part of calculation correctness, not only a performance optimization.
  Debouncing reduces work, while aborting superseded requests prevents an older response from
  replacing the result for newer controls.
- Cancellation can occur after response headers arrive while JSON is still being consumed. Client
  parsing helpers must rethrow abort errors rather than relabel them as malformed API responses.
- In an npm workspace with a hoisted test runner, the runner's environment package must be
  resolvable from the hoist location. Declare the Node-compatible `jsdom` version at the repository
  root and validate with a clean `npm ci`; a populated local dependency tree can otherwise mask the
  same resolution failure that a clean CI runner exposes.
- A custom multi-thumb allocation control adds difficult adjacent-handle and assistive-technology
  semantics. Native per-component range sliders plus a non-editing stacked summary preserve familiar
  controls while showing the whole attribute allocation.
- Percentage editing is deterministic when it operates on 100 integer units: reserve the edited
  share, distribute the remainder proportionally, floor quotas, then assign leftover units by
  largest remainder with formula order as the tie-breaker. Current, baseline, and equal-share
  fallbacks preserve useful peer proportions while guaranteeing an exact `1.00` total.
- Exact client allocation is an authoring policy, not a browser evaluator. The API must still
  validate the complete proposed document, and only the shared Python engine may normalize inputs
  and calculate ratings.
- A valid source formula may use any finite nonnegative component weights with a positive sum because
  the shared engine normalizes them. Show those untouched weights as normalized shares in sliders,
  the allocation bar, and glossary text without rewriting the loaded document; require exactly 100
  integer units only after the designer authors a component change.

### 2026-07-14 — US-013

- A top-overall sample overrepresents elite tiers and hides sensitivity elsewhere in the rating
  curve. Three deterministic representatives per populated tier provide a more useful default design
  cohort while preserving full-cohort percentile and rank calculation on the server.
- Keep representative selection and user pins separate: the former is reproducible from the loaded
  baseline, while the latter is a session-only investigation aid. A fixed ten-pin limit keeps the
  combined 15-player default within the API's 25-player preview bound.
- Rank movement must be calculated over the fixed complete cohort with explicit tie semantics.
  Ranking only the displayed comparison players makes the apparent impact depend on UI sampling.
- A debounced search must invalidate visible results at input time, not request time, or stale pin
  actions remain available under the new query. Session-generation guards must likewise cover both
  success and failure paths so an old request cannot mutate a reloaded session.
- Keeping the selected-player rating summary visible beside weight controls makes the comparison
  loop faster without changing its population: representatives, ranks, and previews still come from
  the API's fixed complete cohort, not the browser's visible sample.
- Mutually exclusive tier, baseline Top 25, and custom-list views are easier to reason about than a
  tier sample with appended pins. Send only the active view's IDs for detailed results and never
  combine hidden view memberships into one preview request.
- A configurable per-tier sample can exceed a fixed selected-player API bound when a future formula
  declares many populated tiers. Detect that condition before preview, show a recovery path, and
  never silently truncate tiers or send a request the API must reject.
- A Top 25 impact view should freeze baseline membership and order while showing preview values and
  rank movement. Resorting or replacing members after each temporary edit changes the question from
  "what happened to these players?" to "who is currently on top?" and makes comparison harder.
- A comparison list and a calculation cohort are different concepts. The browser may choose up to
  25 rows to display, but the server must continue evaluating the complete fixed cohort so switching
  views cannot change percentiles or ranks.
- Baseline and preview columns alone do not make a dense tuning surface easy to scan. Emphasize every
  nonzero authoritative change consistently across summaries, formula-derived component details,
  and comparison results: green for an increased outcome or movement toward rank 1, red for a
  decrease or movement away, blue for a changed weight allocation that is not inherently good or
  bad, and a neutral treatment for no change. Color is only redundant emphasis; signed values,
  arrows, direction words, and accessible labels must communicate the same meaning.
- Scope a custom-list error to the action that produced it. Clear an add failure when the designer
  starts a new search or removes a player, and generation-scope pending add completions so they
  cannot erase or obscure a newer query.
- A failed load in an already active comparison view needs an explicit in-place retry action.
  Requiring the user to switch modes and return hides the recovery path and couples retry behavior
  to navigation.
- Adjacent visible elements do not guarantee a clearly separated accessible name. Give a player
  selector an explicit label that delimits the display name and humanizes its tier identifier while
  retaining the same readable tier in the visible interface.

### 2026-07-14 — implementation alignment

- A documented API maximum is not enforced merely because the default configuration uses it. Apply
  contract ceilings when settings are constructed so alternate YAML, `dataclasses.replace`, and
  embedded callers cannot expand one API version beyond its validated response and performance
  bounds.
- Pins and selected preview players share the same numerical maximum but are different endpoint
  concepts. Give each its own setting, and provide an explicit inheritance rule for older
  configuration rather than retaining accidental coupling in service logic.
- Implement compatibility defaults at the shared settings-construction boundary. A fallback only in
  a YAML parser leaves exported direct constructors with different behavior and can silently broaden
  a caller's previously narrower limit.
- A shared configuration file can safely support current and standalone legacy commands only when
  each command's settings are labeled. Otherwise an unused season filter can look like current
  normalized-publication policy.
- Duplicated third-party prose can retain stale implementation claims after the tracked source
  manifest and data-boundary documentation have become authoritative. Remove the duplicate rather
  than preserving contradictory roadmap text.

### 2026-07-15 — US-016

- Cross-project contract history starts at the first interface accepted by both producer and
  consumer. Internal package evolution should not be presented as NBA-GM contract evolution.
- Keep normative contract identity separate from delivery status. A baseline can be version 1 while
  its machine-readable schemas, fixtures, publishers, and consumers are still being implemented.
- Name the contract family version and profile independently from manifest, package, adapter, and
  formula versions so a shared number does not imply shared compatibility semantics.

## Entry format

Add new entries under a dated heading and identify the story that produced the learning:

```text
### YYYY-MM-DD — US-NNN

- What was learned.
- Why it matters to later stories.
- Any constraint or validation that should be reused.
```
