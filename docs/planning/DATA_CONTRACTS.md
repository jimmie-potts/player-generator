# Proposed version 2 data contracts

These are planned interfaces. They are not emitted by the current implementation. All CSVs use
camelCase headers, UTF-8 encoding, one header row, and stable IDs. Missing optional source values
remain empty rather than being inferred without an approved rule.

## Reference package

| File | Grain | Required identity columns | Purpose |
|---|---|---|---|
| `players.csv` | one row per player | `playerId` | Names, birth date, physical, origin, college, and draft data |
| `player_seasons.csv` | one aggregate row per player-season | `playerSeasonId,playerId,season` | Season context, optional single-team identity, age, games, wins, losses, and minutes |
| `player_stats.csv` | one row per player-season | `playerSeasonId,playerId,season` | Traditional totals and available per-game, per-36, and per-100 rates |
| `player_advanced_stats.csv` | one row per player-season | `playerSeasonId,playerId,season` | Usage, efficiency, rebound, assist, rating, PIE, and win-share metrics |
| `player_source_ids.csv` | one row per player and source | `playerId,sourceType,sourcePlayerId` | Source reconciliation without exposing IDs downstream |
| `sources.csv` | one row per input | `sourceId` | Source type, input filename, hash, schema version, row count, and processing time |

Proposed `players.csv` header:

```text
playerId,displayName,firstName,lastName,birthDate,heightInches,weightPounds,country,college,draftYear,draftRound,draftNumber
```

Proposed `player_seasons.csv` header:

```text
playerSeasonId,playerId,season,teamId,teamAbbreviation,age,games,starts,wins,losses,minutes
```

`teamId` and `teamAbbreviation` are optional on the aggregate season row. They are populated only
when the row represents one team; multi-team labels are source context and must not be converted into
a canonical team ID. Team-stint publication is deferred from contract version 1.

The exact statistical metric columns must be selected from the canonical model during US-005 and
versioned with the contract. Source columns that cannot be mapped without changing meaning remain
source-adapter concerns rather than being copied through verbatim.

## Roster package

| File | Grain | Purpose |
|---|---|---|
| `players.csv` | one row per roster player | Generated identity and available bio or physical fields |
| `player_stats.csv` | one row per roster player and season | Internally consistent adjusted traditional and rate statistics |
| `player_advanced_stats.csv` | one row per roster player and season | Adjusted advanced and possession metrics |
| `player_attributes.csv` | one row per roster player | Calculated attributes, overall, tier, and formula version |
| `manifest.json` | one package | Contract versions, reference-package hash, formula version, seed, and row counts |

Every CSV joins through `playerId`. Upstream names, source IDs, source team IDs, and source-row
indexes are forbidden from roster output.

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
