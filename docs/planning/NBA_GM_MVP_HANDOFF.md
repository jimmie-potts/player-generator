# NBA-GM MVP player data contract version 1

This document is the portable version 1 handoff for the NBA-GM agent. It records the agreed baseline
and proposes NBA-GM review and implementation stories. NBA-GM should reconcile the proposed IDs and
dependencies with its own roadmap before starting them.

[DATA_CONTRACTS.md](DATA_CONTRACTS.md) is the normative version 1 baseline. The player-generator
schemas, publishers, and readers use its two profiles; US-016 and US-017 are recording final
validation and cross-project conformance evidence.

## Agreed MVP boundary

The version 1 roster profile is a private, build-time, manifest-backed integration package:

```text
manifest.json
players.csv
player_stats.csv
player_attributes.csv
```

- `players.csv` contains one generated identity and physical snapshot per player.
- `player_stats.csv` contains one statistical-basis row per player with the governed traditional,
  rate, possession, and advanced observations.
- `player_attributes.csv` remains one formula-derived row per player.
- All CSVs have exactly the same `playerId` set.
- `season` is the four-digit ending year of the statistical season. `2025` means 2024-25.
- Different generated players may have different statistical-basis seasons. Those seasons do not
  set NBA-GM's starting season or league calendar.
- The human-review workbook is generated separately and is never an integration input.

NBA-GM consumes only the roster profile. Within player-generator, the corresponding reference
`players.csv`, `player_stats.csv`, and `player_attributes.csv` files are required to derive shared
fields and formatting from the same authored family resource. The parity validator now rejects any
profile difference outside its closed temporary alignment ledger. US-016 remains in progress for
paired fixtures and final contract decisions; US-017 resolves the pinned profile-schema field,
order, type, and bound gaps as publication adopts the shared definitions. Both version 1 profiles
publish advanced metrics in `player_stats.csv`, while reference season context remains a
reference-only extension. Reference-only source IDs, provenance, reconciliation, and audit data
remain behind the reference boundary and are not added to the NBA-GM handoff.

## Ownership baseline

| Area | MVP owner |
|---|---|
| Generated names, roster player IDs, age, and physical values | player-generator |
| Version 1 traditional, rate, possession, and advanced observations | player-generator |
| Formula-derived player attributes and formula provenance | player-generator |
| Integer statistical season-ending year | player-generator |
| Package integrity and deterministic conformance fixture | player-generator |
| Conversion from `2025` to NBA-GM season key `2024-25` | NBA-GM adapter |
| NBA-GM ID namespace or remapping policy | Joint contract decision; NBA-GM integration |
| Birth date, positions, teams, assignments, and roster status | NBA-GM |
| Contracts, picks, staff, rules, starting season, and league dates | NBA-GM |
| Simulation-specific ratings and tendencies | NBA-GM rating transformation |
| Structured personality defaults required by the MVP | NBA-GM |
| ESPN-derived simulation statistics, deeper metrics, and personality descriptions | Deferred |

Age must not be silently converted into an invented exact birth date. Likewise, player-generator
attributes on the configured 25-99 scale are model outputs, not automatic equivalents of NBA-GM's
broader ratings merely because their numeric ranges overlap.

## Cross-project contract artifacts

The US-016 handoff provides NBA-GM with:

- the authored machine-readable family catalog, exact roster schema, and accepted version 1
  contract identity;
- ordered headers, types, null rules, ranges, units, and primitive or derived classifications;
- one fully synthetic golden package with pinned file and content hashes;
- an expected joined player record;
- explicit decisions for package namespace, player-ID handling, age/effective-date interpretation,
  and the disposition of every version 1 field.

NBA-GM should keep the synthetic fixture self-contained so its tests do not require a
player-generator checkout. The paired reference fixture and cross-profile parity tests remain
player-generator-owned producer checks; NBA-GM does not need to validate or consume the reference
profile.

## Proposed NBA-GM epic: Consume the player-generator MVP roster package

- **Status:** proposed
- **Priority:** MVP
- **Objective:** Validate the agreed player-generator package at the internal data-import boundary,
  preserve its version 1 statistics as first-class MVP observations, convert them into simulation
  inputs through NBA-GM's rating generator, and combine them with NBA-GM-owned league context.

This is a dedicated internal adapter. It does not replace or redefine NBA-GM's public, user-authored
XLSX league-package format.

### Epic acceptance criteria

- NBA-GM and player-generator share the exact version 1 roster schema, semantic field definitions,
  and synthetic conformance fixture.
- NBA-GM accepts the roster profile without taking ownership of player-generator's paired reference
  publication or its private provenance extensions.
- Every version 1 player, statistic, and attribute field has an explicit consumer disposition.
- Statistical observations remain separate from generated ratings, tendencies, and personalities.
- `season = 2025` deterministically becomes `2024-25`, including century-safe formatting.
- Statistical-basis seasons never implicitly set NBA-GM's starting season.
- A valid player package can be combined with NBA-GM-owned context into a playable normalized league
  DTO and save.
- Blocking validation failures never produce partial normalized output or partial saves.
- Committed fixtures contain no real reference rows, provider IDs, private source hashes, or
  provider payloads.
- ESPN-derived simulation statistics, deeper metrics, and personality imports or descriptions
  remain outside this epic.

## NGM-PG-001: Review and accept the MVP handoff contract

- **Status:** proposed
- **Dependencies:** Player-generator version 1 baseline; coordinate with the US-016 schemas and
  fixture

### User story

As an NBA-GM maintainer, I want to review and formally accept the player-generator boundary so both
projects can implement against the same semantics in parallel.

### Acceptance criteria

- Accept or return specific changes for the exact canonical inventory of `manifest.json`,
  `players.csv`, `player_stats.csv`, and `player_attributes.csv`; keep review workbooks outside it.
- Review every table's grain, primary key, ordered header, nullability, type, range, unit, and exact
  relationship.
- Confirm one statistical-basis row and one attribute row per player for the MVP.
- Confirm that the accepted files are the player-generator roster profile; NBA-GM does not ingest
  the paired reference profile or its season-context and provenance extensions.
- Confirm that integer `season` is the ending year, that `2025` means 2024-25, that players may have
  different basis seasons, and that none of those values sets the new league's starting season.
- Give every input field one disposition: direct import, normalized observation, rating-transform
  input, display or history value, validation-only with rationale, or intentionally unsupported with
  rationale.
- Review the classification of primitive totals, derived totals, per-game, per-36, per-100,
  frequency, percentage, and advanced metrics.
- Compare the semantic role and scale of every player-generator attribute with NBA-GM's rating
  model; do not accept a numeric-only mapping.
- Resolve ownership for IDs, age and birth date, positions, assignments, teams, contracts,
  tendencies, personality defaults, and league context.
- Record that the player-only package is an input to league assembly, not a complete
  `LeagueImportDto`.
- Record accepted choices in NBA-GM architecture, import, rating-generator, epic, and decision
  documentation. Do not redefine the public XLSX upload contract.

### Out of scope

- Runtime implementation, ESPN-derived simulation statistics, deeper metrics, and personality
  imports or descriptions.

## NGM-PG-002: Define normalized player-observation DTOs and season conversion

- **Status:** proposed
- **Dependencies:** NGM-PG-001; coordinate with NBA-GM E01 normalized import work

### User story

As a data-import developer, I want source-neutral player-observation DTOs so the adapter can retain
every MVP statistic without conflating observations with simulation ratings.

### Acceptance criteria

- Add strict schemas and TypeScript types for the accepted manifest, player rows, statistical
  observations, calculated attributes, and normalized roster result.
- Keep observations separate from ratings, tendencies, and personalities.
- Amend the normalized league-import boundary to carry observations, or document an explicit
  intermediate roster DTO and assembly boundary.
- Type every accepted statistic and associate it with the agreed unit and classification.
- Preserve optional cells as optional; do not fabricate missing statistical values.
- Keep player-generator formula attributes distinguishable from NBA-GM player-rating DTOs.
- Implement one season converter with at least these cases: `2025` to `2024-25`, `2026` to
  `2025-26`, and `2000` to `1999-00`.
- Reject non-integers and unsupported values before conversion with stable issue codes.
- Ensure a player's converted statistical-basis season is never reused automatically as the
  league's starting season.
- Cover century rollover, invalid inputs, optional behavior, and mixed player seasons in tests.
- Keep provider-specific and ESPN-specific fields out of the normalized contract.

## NGM-PG-003: Pin the cross-project conformance fixture

- **Status:** proposed
- **Dependencies:** NGM-PG-001 and player-generator US-016 fixture

### User story

As a maintainer of either project, I want a shared synthetic fixture and expected normalization
result so producer and consumer changes cannot silently drift apart.

### Acceptance criteria

- Check in the small, fully synthetic package supplied by player-generator, exercising every
  contracted column, representative optional nulls, percentage scales, signed metrics, and at least
  two season-ending years.
- Check in the expected normalized NBA-GM result, including canonical season conversions.
- Pin the accepted schema identifier and the fixture's declared file and content hashes.
- Prove that parsing preserves values, numeric precision, nulls, and row relationships.
- Add negative coverage for manifest or file hash mismatch; missing or extra files; missing, extra,
  reordered, or duplicate headers; duplicate players; mismatched player relationships; invalid,
  non-finite, or out-of-range values; invalid seasons; and governed formula-metadata mismatch.
- Derive negative variants in tests where practical rather than maintaining many package copies.
- Keep the fixture self-contained and free of real people, source IDs, private hashes, and provider
  payloads.

## NGM-PG-004: Implement the manifest-backed CSV adapter

- **Status:** proposed
- **Dependencies:** NGM-PG-002 and NGM-PG-003

### User story

As NBA-GM, I want to validate and parse the player-generator package at a dedicated boundary so
invalid or tampered input cannot reach domain or save-creation code.

### Acceptance criteria

- Implement a dedicated adapter in NBA-GM's data-import package that recognizes only the accepted
  player-generator package.
- Validate the manifest contract identity, exact canonical file set, declared row counts, individual
  file hashes, and aggregate content identity before accepting the normalized result.
- Validate encoding, exact ordered headers, scalar types, required and null rules, enums, bounds,
  and finite numbers.
- Require unique IDs and the exact same player set across players, statistics, and attributes.
- Require exactly one statistics and one attribute row per MVP player.
- Normalize the statistics season through the one converter from NGM-PG-002.
- Return stable issues with severity, code, file, row, column, message, and a useful fix when
  available. A blocking issue returns no partial normalized DTO.
- Keep save creation, roster assignment, rating generation, personality generation, and contract
  generation outside the adapter.
- Make repeated parsing of identical bytes produce deeply equal normalized output.
- Avoid logging complete rows or exposing private manifest provenance in diagnostics.
- Pass all positive and negative NGM-PG-003 conformance tests.

## NGM-PG-005: Generate simulation inputs from MVP observations

- **Status:** proposed
- **Dependencies:** NGM-PG-004 and NBA-GM rating-generator MVP work

### User story

As the simulation model, I want deterministic ratings and tendencies derived from the imported MVP
observations so the collected statistics materially contribute to gameplay.

### Acceptance criteria

- Keep the transformation in NBA-GM's rating-generator boundary, not in the CSV adapter, domain
  entities, API, UI, or possession simulator.
- Accept the normalized version 1 statistics and the formula-derived attributes approved by
  NGM-PG-001.
- Produce NBA-GM's complete MVP rating and tendency shapes.
- Honor the field-disposition matrix; do not silently drop a version 1 statistic or attribute. Fields
  intentionally unused by the first formula retain their observations and have documented rationale.
- Avoid double-counting primitive and derived metrics and handle each percentage scale explicitly.
- Map 25-99 player-generator attributes semantically rather than treating them as interchangeable
  with NBA-GM's 0-100 concepts.
- Supply missing NBA-GM concepts only through documented deterministic priors, seeded rules, or a
  blocking error selected during NGM-PG-001.
- Record the transformation version, input package identity, player-generator formula identity, and
  sufficient trace information to explain generated values.
- Make identical inputs and seed produce identical results, with focused tests showing that
  representative input changes affect the intended outputs.
- Keep raw observations accessible and separate from the generated ratings and tendencies.
- Do not infer personality values or descriptions from statistics in this story.

## NGM-PG-006: Assemble and retain the roster in an NBA-GM league

- **Status:** proposed
- **Dependencies:** NGM-PG-004, NGM-PG-005, NBA-GM normalized-save work, and an NBA-GM-owned source
  of league context

### User story

As an MVP league creator, I want to combine the imported player roster with NBA-GM-owned context so
it can create a playable, traceable save without assigning responsibilities to the wrong project.

### Acceptance criteria

- Combine imported players, observations, attributes, and generated simulation inputs with
  NBA-GM-owned teams, positions, assignments, roster statuses, contracts, staff, picks, rules, and
  league dates.
- Keep the CSV adapter from inventing missing context.
- Follow the accepted age-to-birth-date and ID namespace rules; never fabricate an exact birth date
  from age alone without an approved deterministic policy.
- Return typed blocking issues for missing required context before save creation.
- Produce the complete normalized league DTO and use the existing atomic save-creation boundary.
- Retain the imported basic statistics in save-owned observation or history records rather than
  discarding them after rating generation.
- Make observations queryable by player and canonical statistical-basis season.
- Record package content identity, formula metadata, and NBA-GM transformation version without
  exposing private provenance in ordinary responses.
- Keep mixed observation seasons independent of the configured league starting season.
- Make save creation atomic and idempotent; deleting the local source package afterward must not
  break the save.
- Prove one representative statistic passes through validation, normalization, rating generation,
  save creation, and later observation retrieval.

## Dependency sequence

```text
Player-generator US-016 contract and fixture
                    |
               NGM-PG-001
                /       \
         NGM-PG-002   NGM-PG-003
                \       /
               NGM-PG-004
                    |
               NGM-PG-005
                    |
               NGM-PG-006
```

The public spreadsheet-import milestone is not a prerequisite for this internal adapter. NBA-GM
should reconcile NGM-PG-002 and NGM-PG-006 with its normalized DTO and atomic-save stories, and
treat NGM-PG-005 as the MVP slice of its rating-generator roadmap.
