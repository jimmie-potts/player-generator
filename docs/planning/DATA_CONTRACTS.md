# Version 2 data contracts

Reference contract version 1 is implemented by US-005; additive reference contract version 2 adds
calculated player-season attributes in US-015. Roster contract version 1 is implemented by US-009.
Coach and team sections remain planned interfaces for their later stories. All CSVs use camelCase
headers, UTF-8 encoding, one header row, LF line endings, and stable IDs. Missing optional source
values remain empty rather than being inferred without an approved rule.

Every integer `season` is the four-digit year in which the basketball season ends: `2025` means the
2024-25 season. In roster output, that value identifies the generated player's statistical basis; it
does not declare a package-wide league season and may differ between players.

## Reference package

| File | Grain | Required identity columns | Purpose |
|---|---|---|---|
| `players.csv` | one row per player | `playerId` | Names, birth date, physical, origin, college, and draft data |
| `player_seasons.csv` | one aggregate row per player-season | `playerSeasonId,playerId,season` | Season context, optional single-team identity, age, games, wins, losses, and minutes |
| `player_stats.csv` | one row per player-season | `playerSeasonId,playerId,season` | Traditional totals and available per-game, per-36, and per-100 rates |
| `player_advanced_stats.csv` | one row per player-season | `playerSeasonId,playerId,season` | Usage, efficiency, rebound, assist, rating, PIE, and win-share metrics |
| `player_attributes.csv` | one row per player-season | `playerSeasonId,playerId,season` | Calculated attributes, overall, tier, and formula version (version 2) |
| `player_source_ids.csv` | one row per player and source | `playerId,sourceType,sourcePlayerId` | Source reconciliation without exposing IDs downstream |
| `sources.csv` | one row per input | `sourceId` | Source type, input filename, hash, schema version, row count, and processing timestamp |

Version 1 `players.csv` header:

```text
playerId,displayName,firstName,lastName,birthDate,heightInches,weightPounds,country,college,draftYear,draftRound,draftNumber
```

Version 1 `player_seasons.csv` header:

```text
playerSeasonId,playerId,season,teamId,teamAbbreviation,age,games,starts,wins,losses,minutes
```

`teamId` and `teamAbbreviation` are optional on the aggregate season row. They are populated only
when the row represents one team; multi-team labels are source context and must not be converted into
a canonical team ID. Team-stint publication is deferred from contract version 1.

Version 1 `player_stats.csv` header:

```text
playerSeasonId,playerId,season,fieldGoalsMade,fieldGoalsAttempted,threePointersMade,threePointersAttempted,freeThrowsMade,freeThrowsAttempted,reboundsOffensive,reboundsDefensive,reboundsTotal,assists,turnovers,steals,blocks,foulsPersonal,points,plusMinusPoints,twoPointersMade,twoPointersAttempted,twoPointPercentage,minutesPerGame,threePointAttemptsPer36,freeThrowAttemptsPer36,offensiveReboundsPer36,defensiveReboundsPer36,assistsPer36,turnoversPer36,stealsPer36,blocksPer36,pointsPer36,plusMinusPer36,pointsPer100,assistsPer100,turnoversPer100,stealsPer100,blocksPer100,twoPointAttemptFrequency,threePointAttemptFrequency
```

Version 1 `player_advanced_stats.csv` header:

```text
playerSeasonId,playerId,season,estimatedOffensiveRating,offensiveRating,estimatedDefensiveRating,defensiveRating,estimatedNetRating,netRating,assistPercentage,assistTurnoverRatio,assistRatio,offensiveReboundPercentage,defensiveReboundPercentage,reboundPercentage,estimatedTurnoverPercentage,effectiveFieldGoalPercentage,trueShootingPercentage,usagePercentage,playerImpactEstimate,defensiveWinShares,defensiveWinSharesPer36
```

Version 1 provenance headers:

```text
player_source_ids.csv: playerId,sourceType,sourcePlayerId
sources.csv: sourceId,sourceType,originalFilename,sha256,adapterVersion,upstreamVersion,rowCount,processedAt,licenseStatus
```

Reference contract version 2 `player_attributes.csv` header:

```text
playerSeasonId,playerId,season,insideScoring,threePointShooting,freeThrowShooting,scoringVolume,playmaking,ballSecurity,offensiveRebounding,defensiveRebounding,perimeterDefense,interiorDefense,stamina,durability,overall,impactPercentile,talentTier,formulaVersion
```

The packaged `reference-v1.schema.json` and `reference-v2.schema.json` resources are the
machine-readable authorities for ordered headers, scalar types, required and nullable fields,
unique keys, and relationships. Version 1 requires the season, traditional-stat, and advanced-stat
tables to contain exactly the same `(playerSeasonId, playerId, season)` key set; version 2 adds the
attribute table to that exact set. Attribute values may be empty when formula eligibility or inputs
do not support them, while the three identity fields and `formulaVersion` remain populated. Source
columns that cannot be mapped without changing meaning remain adapter concerns rather than being
copied through verbatim.

Each published reference package also contains `audit.json` and `manifest.json`. The manifest
records contract versions, input hashes and adapter versions, file row counts and hashes, and one
content hash over every contracted CSV plus the deterministic audit. Version 2 also records the
formula version and exact formula-document hash. `createdAt` is explicitly excluded from the
content hash.

## Roster package

| File | Grain | Purpose |
|---|---|---|
| `players.csv` | one row per roster player | Generated identity and available bio or physical fields |
| `player_stats.csv` | one row per roster player for its generated season | Internally consistent adjusted traditional and rate statistics |
| `player_advanced_stats.csv` | one row per roster player for its generated season | Adjusted advanced and possession metrics |
| `player_attributes.csv` | one row per roster player | Calculated attributes, overall, tier, and formula version |
| `manifest.json` | one package | Contract versions, reference-package hash, formula version, seed, and row counts |

Every CSV joins through `playerId`. Upstream names, source IDs, source team IDs, and source-row
indexes are forbidden from roster output.

Roster contract version 1 permits exactly one traditional-stat row and one advanced-stat row per
player. The two rows must also share the same `(playerId, season)` key. Attributes remain at player
grain, so allowing a second stat season would make the rated season ambiguous.

Version 1 `players.csv` header:

```text
playerId,displayName,firstName,lastName,age,heightInches,weightPounds
```

Names and IDs are generated independently of the sampled template. Age, height, and weight are
nullable and are adjusted only when the selected reference row supplies the corresponding value.

Version 1 `player_stats.csv` header:

```text
playerId,season,games,minutes,possessions,fieldGoalsMade,fieldGoalsAttempted,twoPointersMade,twoPointersAttempted,threePointersMade,threePointersAttempted,freeThrowsMade,freeThrowsAttempted,reboundsOffensive,reboundsDefensive,reboundsTotal,assists,turnovers,steals,blocks,foulsPersonal,points,plusMinusPoints,fieldGoalPercentage,twoPointPercentage,threePointPercentage,freeThrowPercentage,minutesPerGame,pointsPerGame,reboundsPerGame,assistsPerGame,turnoversPerGame,threePointAttemptsPer36,freeThrowAttemptsPer36,offensiveReboundsPer36,defensiveReboundsPer36,assistsPer36,turnoversPer36,stealsPer36,blocksPer36,pointsPer36,plusMinusPer36,pointsPer100,assistsPer100,turnoversPer100,stealsPer100,blocksPer100,twoPointAttemptFrequency,threePointAttemptFrequency
```

`season`, `games`, and `minutes` come from the selected eligible player-season. `possessions` is the
single controlled possession basis defined by D-018. Makes, attempts, and event totals are mutated
first; field-goal totals, points, rebound totals, percentages, and every per-game, per-36, and
per-100 field are derived afterward. Rebound, foul, and plus-minus values remain empty when their
source total or supported rate is unavailable.

Version 1 `player_advanced_stats.csv` header:

```text
playerId,season,estimatedOffensiveRating,offensiveRating,estimatedDefensiveRating,defensiveRating,estimatedNetRating,netRating,assistPercentage,assistTurnoverRatio,assistRatio,offensiveReboundPercentage,defensiveReboundPercentage,reboundPercentage,estimatedTurnoverPercentage,effectiveFieldGoalPercentage,trueShootingPercentage,usagePercentage,playerImpactEstimate,defensiveWinShares,defensiveWinSharesPer36
```

Net ratings, shooting percentages, assist/turnover ratio, and defensive win shares per 36 are
derived from their published operands. Effective field-goal and true-shooting rates allow the
mathematically valid range 0–1.5 rather than treating them as ordinary proportions.
`assistTurnoverRatio` uses `assists / max(turnovers, 1)` so a zero-turnover line remains finite.
`assistRatio` and `estimatedTurnoverPercentage` share the play-ending denominator
`fieldGoalsAttempted + 0.44 * freeThrowsAttempted + assists + turnovers`. Rebound percentage
remains a separately mapped, bounded source metric rather than an arithmetic mean of the offensive
and defensive values. Other available advanced values receive bounded controlled mutation.

Version 1 `player_attributes.csv` header:

```text
playerId,insideScoring,threePointShooting,freeThrowShooting,scoringVolume,playmaking,ballSecurity,offensiveRebounding,defensiveRebounding,perimeterDefense,interiorDefense,stamina,durability,overall,impactPercentile,talentTier,formulaVersion
```

The packaged `roster-v1.schema.json` resource governs ordered headers, scalar types, nullability,
bounds, per-player stat-row uniqueness, exact player and player-season key sets, and relationships.
Semantic validation also recomputes every published statistical identity before publication.

`manifest.json` is deterministic and records manifest and package version 1, every CSV contract
version, the reference-package content hash, formula version and document hash, seed, semantic
configuration hash, per-file row counts and hashes, and one aggregate content hash. It intentionally
has no creation timestamp. Publication writes a same-parent staging directory and replaces the
destination only after contract, relationship, statistical, integrity, and identity-leak checks
pass.

## Planned parity-aligned NBA-GM MVP player contracts

The following is the agreed EPIC-08 target, not either implemented interface above. Reference
version 2 and roster version 1 remain current until US-017 completes. US-016 freezes two profiles of
one player-data contract and paired synthetic fixtures; US-017 changes both publishers, their
supported readers, and current-state documentation together after NBA-GM can review the roster
profile.

Planned reference profile:

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

Planned roster profile and exact NBA-GM handoff:

```text
manifest.json
players.csv
player_stats.csv
player_attributes.csv
```

| Corresponding file | Reference grain and key prefix | Roster grain and key prefix | Shared payload |
|---|---|---|---|
| `players.csv` | one row per reference player; `playerId` | one row per roster player; `playerId` | Approved player identity, bio, and physical fields |
| `player_stats.csv` | one row per player-season; `playerSeasonId,playerId,season` | one row per roster player for its sole statistical-basis season; `playerId,season` | Traditional, rate, possession, and advanced observations |
| `player_attributes.csv` | one row per player-season; `playerSeasonId,playerId,season` | one row per roster player; `playerId` | Formula-derived attributes, overall, percentile, tier, and formula identity |

The corresponding files derive their shared payload from one definition. Shared fields retain the
same relative order, scalar representation, meaning, null encoding, unit or scale, bounds or enum,
primitive or derived classification, and CSV serialization in both profiles. New player-content
fields default to both profiles. A field present in only one profile requires a dated decision and
an explicit extension declaration. Parity does not require equal row values, IDs, grains, or full
package inventories.

US-016 must close and govern the extension list. Reference-only `playerSeasonId` keys, season
context, source IDs, provenance, reconciliation, audit data, and availability-based null rules do
not enter roster data. Roster-only generator, namespace, ID-scheme, seed, configuration, and
reference-package metadata do not become reference placeholders. A profile extension cannot change
a shared field's type, meaning, unit, bounds, or derivation. The contract must explicitly resolve
current differences such as `age` versus `birthDate`, count-number representation, and fields
available in only one current profile without fabricating values.

Both target profiles consolidate their traditional and advanced metrics into `player_stats.csv` and
retire `player_advanced_stats.csv`. The shared statistics payload includes the governed games,
minutes, possession basis, percentages, and rate fields. If reference `player_seasons.csv` retains a
value also published in `player_stats.csv`, relationship validation requires exact equality instead
of permitting two independently mutable definitions.

The manifests share a governed envelope for package type and contract identity, file row counts and
hashes, formula identity, and aggregate content identity. Reference input, provenance, and audit
metadata and roster generation metadata remain declared profile extensions. Cross-profile tests
compare the shared definitions after declared key prefixes, exercise identical serialization in
paired synthetic fixtures, reject undeclared fields or overrides, and prove that a one-sided field,
ordering, type, or formatting change fails.

The roster profile's three CSVs have the exact same unique `playerId` set. Its single `season` value
is the statistical season-ending year from D-031 and is not NBA-GM league context. NBA-GM converts
that value to its canonical `YYYY-YY` key, validates only the roster profile, retains all current
statistics as MVP observations, and owns positions, team assignment, contracts, league dates,
detailed simulation ratings, and tendencies.

The handoff retains a contract identifier but requires no pre-integration compatibility or
dual-publishing path. A generated `roster-review.xlsx` may project the consolidated statistics into
human-oriented sheets, but it remains outside the package directory, manifest, and content hash and
cannot write changes back to canonical data.

ESPN-derived simulation statistics, deeper metrics, and personality traits or descriptions remain
post-MVP work. Source-specific IDs and fields continue to stop at the reference boundary; later
shared player fields require a parity-aligned contract change. See
[NBA_GM_MVP_HANDOFF.md](NBA_GM_MVP_HANDOFF.md) for the ownership boundary and proposed NBA-GM
consumer stories.

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
