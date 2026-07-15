# Player data contract version 1

Version 1 is the baseline player-data contract shared by player-generator and NBA-GM. It defines
one contract family with two publication profiles:

- the `reference` profile contains calibrated player-season data and private provenance; and
- the `roster` profile contains generated player data and is the only profile consumed by NBA-GM.

The baseline format is established by
[D-034](DECISIONS.md#d-034-player-data-contract-version-1-baseline), with its exact current
inventory fixed by [D-035](DECISIONS.md#d-035-current-version-1-package-inventory) and its shared
physical representation fixed by
[D-036](DECISIONS.md#d-036-shared-physical-measurement-representation). Shared advanced-metric
bounds are fixed by [D-037](DECISIONS.md#d-037-lossless-shared-advanced-metric-bounds), under
EPIC-08.
The machine-readable schemas, publishers, and readers implement the exact version 1 inventories and
accept no earlier normalized package layout. The shared contract-family resource now owns the target
common field definitions, semantic metadata, declared extensions, availability overrides, and CSV
rules. Its alignment ledger records the remaining differences in the current runtime profile
schemas. US-016 owns the catalog, declarations, paired synthetic fixtures, and final contract
decisions; US-017 owns removing the runtime-schema gaps while applying the aligned profile to
publication behavior.

## Contract identity

- The player-data contract family version is the integer `1`.
- Every package identifies its profile as `reference` or `roster`.
- Profile, manifest, package, adapter, and formula identifiers are separate version domains. In
  particular, `formulaVersion` identifies the formula document and does not change the player-data
  contract version.
- A change to shared file inventory, field meaning, field order, type, null rule, unit, bound,
  derivation, relationship, or CSV serialization is a contract change.
- The version 1 resources freeze the exact manifest field names and schema resource names. Those
  names identify the contract family, version, and profile without ambiguity; US-016 tracks their
  final conformance validation.

## Common conventions

All contracted CSVs use:

- camelCase headers in an exact governed order;
- UTF-8 encoding;
- one header row;
- comma delimiters with minimal double-quote escaping;
- LF line endings;
- an empty cell for a permitted null;
- canonical finite-number serialization using the shortest round-trip significand expanded to plain
  base-10 notation without an exponent, with no insignificant fractional zeros, no decimal point
  for integral values, and `0` for negative zero; and
- stable deterministic row ordering.

Unavailable optional values remain empty. They are never inferred or fabricated without an approved
rule. Version 1 requires shared fields to use the same name, relative order, scalar representation,
meaning, null encoding, unit or scale, bounds or enum, primitive or derived classification, and CSV
formatting in both profiles. `schemas/player-data-v1.contract.json` is the authored source for those
rules. `validate_player_data_profile_parity()` compares both current profile resources with that
source and fails for a new discrepancy or a declared discrepancy that no longer exists.
Each declaration pins the exact temporary value or complete shared order; it does not waive an
entire field or file from further drift checks.

Every integer `season` is the four-digit year in which the basketball season ends. `2025` means the
2024-25 season. In the roster profile, this is the statistical-basis season for one generated
player; it does not set NBA-GM's league season and may differ between players in the same package.

## Current alignment state

The family resource separates the final shared definition from the current publication state. Its
closed temporary ledger currently records only these unresolved runtime-schema differences:

- reference `player_stats.csv` does not yet emit the seven shared derived fields
  `fieldGoalPercentage`, `threePointPercentage`, `freeThrowPercentage`, `pointsPerGame`,
  `reboundsPerGame`, `assistsPerGame`, and `turnoversPerGame`;
- reference still orders its two-point totals after `plusMinusPoints`; and
- the expanded profile resources have not yet adopted the shared integer count types, bounded
  precision-preserving physical number representation, four-digit season bounds, and rate,
  percentage, frequency, and rating bounds.

Those seven statistics are shared fields, not roster extensions. `possessions` is the only
roster-only statistics extension. The expanded reference and roster schemas remain authoritative
for currently runnable packages until the declared work is applied; the ledger prevents that
temporary state from being mistaken for an accepted contract difference. US-016 remains
`in_progress` while its fixtures and remaining contract decisions are completed, and no gap may be
added without an explicit rationale and follow-up story. Canonical serializer adoption, manifest
alignment, package namespace, and age/effective-date behavior remain separately tracked work rather
than unlisted schema gaps.

## Version 1 profile inventories

Reference profile:

```text
manifest.json
audit.json
players.csv
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
| `player_stats.csv` | one row per player-season; `playerSeasonId,playerId,season` | one row per roster player for its statistical-basis season; `playerId,season` | Traditional, rate (including per-100), and advanced observations |
| `player_attributes.csv` | one row per player-season; `playerSeasonId,playerId,season` | one row per roster player; `playerId` | Formula-derived attributes, overall, percentile, tier, and formula identity |

The shared content in these files must derive from one definition. Profile-specific key prefixes
are declared extensions and do not alter the shared field definitions that follow them. New
player-content fields default to both profiles. A field present in only one profile requires a dated
decision and an explicit extension declaration. The family validator now enforces that closed
extension set and permits only declared required/null availability overrides. The remaining
materialized-schema differences are the temporary gaps listed above, not profile extensions.

Parity does not require equal row values, IDs, grains, or complete package inventories. It requires
the two profiles to agree wherever they represent the same player-data concept.

### `players.csv`

The shared definition governs `playerId`, display and component names, height, and weight. Reference
identity and roster identity use separate namespaces even though the key has the same name.

Height and weight are bounded numbers so reference data can preserve fractional precision while
generated whole-unit roster values remain valid without rounding or conversion.

Reference-only player fields may include birth date, origin, college, and draft facts because they
belong to reference identity and provenance. Roster-only `age` is a generated snapshot owned by
player-generator. Age is not converted into an invented birth date, and NBA-GM owns any birth-date
rule needed by its league model.

The version 1 family freezes the exact ordered columns, types, base null rules, meanings, units,
classifications, and bounds. Shared definitions cannot be weakened or reinterpreted by a profile
extension. Reference physical-field alignment remains explicitly tracked rather than silently
accepted as a second definition.

### `player_stats.csv`

Version 1 publishes traditional totals, rate statistics, and advanced metrics in one ordered row.
Shared count, percentage, frequency, rating, per-game, per-36, and per-100 fields have one governed
representation and semantic definition across both profiles. The roster profile additionally
requires an explicit `possessions` total; the reference profile publishes per-100 rates but no
possession total.

The shared catalog includes all seven derivable percentages and per-game rates that the current
reference schema still lacks. They remain in the alignment ledger until US-017 populates and
publishes them; they are never treated as roster-only content.

The reference key prefix is `playerSeasonId,playerId,season`. The roster key prefix is
`playerId,season`, and each roster player has exactly one statistics row. Makes, attempts, points,
rebound totals, percentages, and rate fields retain their declared arithmetic relationships.
Effective field-goal and true-shooting rates permit the mathematically valid range 0–1.5.
Offensive and defensive ratings are nonnegative with no artificial upper ceiling. Net ratings and
the dimensionless `playerImpactEstimate` index are unbounded finite values so valid negative and
small-sample reference observations are not discarded merely because generated roster values
occupy a narrower range.

The reference row retains its player-season context directly in `player_stats.csv`, including the
governed season, team context when unambiguous, age, games, starts, wins, losses, and minutes. These
values have one authoritative representation rather than a second mutable season-context surface.

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

- season context and source-only observations declared as `player_stats.csv` profile extensions;
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
- Reference statistics and attribute rows use the same `(playerSeasonId, playerId, season)` key set.
- Roster `players.csv`, `player_stats.csv`, and `player_attributes.csv` use the exact same unique
  `playerId` set.
- Each roster player has exactly one statistical-basis season and one attribute row.
- Cross-profile contract tests compare both expanded schemas to the one shared field catalog,
  including ordered fields, types, base null rules and declared overrides, units, bounds, semantic
  metadata, derivation classifications, and serialization rules.
- A one-sided shared-field change, undeclared extension, order change, type change, or constraint
  change fails unless it exactly matches a declared temporary gap. A stale gap also fails.
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
