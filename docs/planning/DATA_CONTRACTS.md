# Player data contract version 1

Version 1 is the baseline player-data contract shared by player-generator and NBA-GM. It defines
one contract family with two publication profiles:

- the `reference` profile contains calibrated player-season data and private provenance; and
- the `roster` profile contains generated player data and is the only profile consumed by NBA-GM.

The baseline format is established by
[D-034](DECISIONS.md#d-034-player-data-contract-version-1-baseline) under EPIC-08. US-016 is
responsible for freezing the machine-readable schemas and synthetic conformance fixtures, and
US-017 is responsible for making both publishers emit those schemas. Until those stories complete,
this document is the normative integration baseline rather than a claim about current command
output.

## Contract identity

- The player-data contract family version is the integer `1`.
- Every package identifies its profile as `reference` or `roster`.
- Profile, manifest, package, adapter, and formula identifiers are separate version domains. In
  particular, `formulaVersion` identifies the formula document and does not change the player-data
  contract version.
- A change to shared file inventory, field meaning, field order, type, null rule, unit, bound,
  derivation, relationship, or CSV serialization is a contract change.
- The exact manifest field names and schema resource names must be frozen by US-016 and identify the
  contract family, version, and profile without ambiguity.

## Common conventions

All contracted CSVs use:

- camelCase headers in an exact governed order;
- UTF-8 encoding;
- one header row;
- LF line endings;
- an empty cell for a permitted null;
- locale-independent finite-number serialization; and
- stable deterministic row ordering.

Unavailable optional values remain empty. They are never inferred or fabricated without an approved
rule. Shared fields use the same name, relative order, scalar representation, meaning, null
encoding, unit or scale, bounds or enum, primitive or derived classification, and CSV formatting in
both profiles.

Every integer `season` is the four-digit year in which the basketball season ends. `2025` means the
2024-25 season. In the roster profile, this is the statistical-basis season for one generated
player; it does not set NBA-GM's league season and may differ between players in the same package.

## Version 1 profile inventories

Reference profile:

```text
manifest.json
audit.json
players.csv
player_seasons.csv
player_stats.csv
player_attributes.csv
player_source_ids.csv
sources.csv
```

Roster profile and exact NBA-GM handoff:

```text
manifest.json
players.csv
player_stats.csv
player_attributes.csv
```

No additional canonical file is permitted in either package. A generated `roster-review.xlsx`
remains outside the package directory, manifest, and content hash and cannot write changes back to
canonical data.

## Corresponding player files

| File | Reference grain and key prefix | Roster grain and key prefix | Governed shared content |
|---|---|---|---|
| `players.csv` | one row per reference player; `playerId` | one row per roster player; `playerId` | Player identity, names, and physical fields |
| `player_stats.csv` | one row per player-season; `playerSeasonId,playerId,season` | one row per roster player for its statistical-basis season; `playerId,season` | Traditional, rate, possession, and advanced observations |
| `player_attributes.csv` | one row per player-season; `playerSeasonId,playerId,season` | one row per roster player; `playerId` | Formula-derived attributes, overall, percentile, tier, and formula identity |

The shared content in these files derives from one definition. Profile-specific key prefixes are
declared extensions and do not alter the shared field definitions that follow them. New
player-content fields default to both profiles. A field present in only one profile requires a dated
decision and an explicit extension declaration.

Parity does not require equal row values, IDs, grains, or complete package inventories. It requires
the two profiles to agree wherever they represent the same player-data concept.

### `players.csv`

The shared definition governs `playerId`, display and component names, height, and weight. Reference
identity and roster identity use separate namespaces even though the key has the same name.

Reference-only player fields may include birth date, origin, college, and draft facts because they
belong to reference identity and provenance. Roster-only `age` is a generated snapshot owned by
player-generator. Age is not converted into an invented birth date, and NBA-GM owns any birth-date
rule needed by its league model.

US-016 must freeze the exact ordered columns, types, null rules, units, and bounds. Shared
definitions cannot be weakened or reinterpreted by a profile extension.

### `player_stats.csv`

Version 1 publishes traditional totals, rate statistics, possession-basis values, and advanced
metrics in one ordered row. Shared count, percentage, frequency, rating, per-game, per-36, and
per-100 fields have one governed representation and semantic definition across both profiles.

The reference key prefix is `playerSeasonId,playerId,season`. The roster key prefix is
`playerId,season`, and each roster player has exactly one statistics row. Makes, attempts, points,
rebound totals, percentages, and rate fields retain their declared arithmetic relationships.
Effective field-goal and true-shooting rates permit the mathematically valid range 0–1.5.

Reference `player_seasons.csv` retains season context. When it repeats `season`, `games`, or
`minutes` from `player_stats.csv`, relationship validation requires exact equality rather than two
independently mutable values.

### `player_attributes.csv`

The shared attribute payload contains the formula-derived skill ratings, `overall`,
`impactPercentile`, `talentTier`, and `formulaVersion`. Ratings use the configured 25–99 scale,
percentiles use 0–1, and the governed tier enum is shared across profiles.

The reference profile may contain empty calculated values when formula eligibility or source inputs
do not support them. The roster profile requires complete calculated values for every generated
player. This availability-based nullability difference is an explicit profile override; it does not
change field meaning, type, scale, or formula identity.

## Profile extensions

Reference-only files and content:

- `player_seasons.csv` for aggregate season context;
- `player_source_ids.csv` for source reconciliation;
- `sources.csv` for source type, filename, hash, adapter version, upstream version, row count,
  processing timestamp, and license status;
- `audit.json` for deterministic reconciliation and publication audit details; and
- reference manifest fields for inputs, provenance, and audit identity.

Roster-only content:

- generated namespace and player-ID scheme;
- deterministic seed and semantic configuration identity;
- generator identity;
- consumed reference-package identity; and
- roster manifest fields required to reproduce generation.

Source identities, source player names, source team IDs, source-row indexes, reconciliation
mappings, and a source-to-roster crosswalk are forbidden from the roster profile.

## Manifest and integrity requirements

Both profiles use a common manifest envelope for:

- contract family, version, and profile;
- exact canonical file inventory;
- per-file row counts and SHA-256 hashes;
- formula identity;
- aggregate deterministic content identity; and
- declared profile extensions.

Reference input, provenance, and audit metadata and roster generation metadata remain profile
extensions. Creation timestamps are excluded from deterministic content identity. A package is
written atomically only after contract, relationship, semantic, integrity, and identity-boundary
validation succeeds.

## Relationship and conformance requirements

- Every foreign key resolves within its package.
- Reference season, statistics, and attribute rows use the same
  `(playerSeasonId, playerId, season)` key set.
- Roster `players.csv`, `player_stats.csv`, and `player_attributes.csv` use the exact same unique
  `playerId` set.
- Each roster player has exactly one statistical-basis season and one attribute row.
- Cross-profile contract tests compare shared ordered fields, types, base null rules and declared
  overrides, units, bounds, semantic metadata, derivation classifications, and serialization.
- A one-sided shared-field change, undeclared extension, order change, type change, or formatting
  difference fails validation.
- Paired synthetic fixtures exercise every shared field and prove that common values serialize
  identically. The roster fixture is self-contained so NBA-GM tests do not require a
  player-generator checkout.
- Manifest, row-count, hash, key-set, duplicate-row, range, non-finite-number, and relationship
  failures produce actionable errors and no partial package.

## NBA-GM ownership boundary

NBA-GM validates and consumes only the roster profile. It converts statistical-basis seasons to its
canonical `YYYY-YY` keys and owns positions, teams, assignments, contracts, league dates, detailed
simulation ratings, tendencies, and personality behavior. It does not ingest the reference profile
or its private extensions.

ESPN-derived simulation statistics, deeper tracking or play-type metrics, personality traits or
descriptions, teams, and coaches are outside version 1.

## Future coach contract

```text
coachId,firstName,lastName,displayName,teamId,role,birthDate,offensiveSystem,defensiveSystem,pacePreference,rotationSize,offenseRating,defenseRating,playerDevelopment,motivation,discipline,adaptability,leadership
```

## Future team contract

```text
teamId,city,nickname,displayName,abbreviation,conference,division,arenaName,marketSize,prestige,primaryColor,secondaryColor
```

Coach ratings and preferences use 0–100. Dates use ISO 8601. Team membership is represented by
`teamId`, not an embedded roster array. These future contracts are design targets only.
