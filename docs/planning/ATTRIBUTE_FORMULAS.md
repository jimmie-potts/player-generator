# Proposed player attribute formulas

This document captures the initial formula contract to be implemented by US-006 and US-007. It
preserves the explainable version 1 baseline while moving definitions out of Python.

## Output schema

```text
playerId,insideScoring,threePointShooting,freeThrowShooting,scoringVolume,playmaking,ballSecurity,offensiveRebounding,defensiveRebounding,perimeterDefense,interiorDefense,stamina,durability,overall,impactPercentile,talentTier,formulaVersion
```

Attributes use a 25–99 rating scale. Each component metric is converted to a season-relative
percentile, combined using normalized weights, ranked again where required, and mapped through
configurable percentile anchors. A component marked `inverse` treats lower raw values as better.

| Attribute | Components |
|---|---|
| `insideScoring` | adjusted 2P% 50%, 2PA frequency 30%, free-throw rate 20% |
| `threePointShooting` | adjusted 3P% 60%, 3PA frequency 40% |
| `freeThrowShooting` | adjusted FT% 100% |
| `scoringVolume` | points/100 50%, usage 30%, TS% 20% |
| `playmaking` | assist percentage 30%, assists/36 25%, assist ratio 15%, assist-to-turnover 15%, usage 15% |
| `ballSecurity` | inverse turnover percentage 40%, assist-to-turnover 30%, inverse turnovers/100 30% |
| `offensiveRebounding` | offensive rebound percentage 100% |
| `defensiveRebounding` | defensive rebound percentage 100% |
| `perimeterDefense` | steals/100 45%, inverse estimated defensive rating 20%, defensive win shares/36 15%, defensive rebound percentage 10%, PIE 10% |
| `interiorDefense` | blocks/100 35%, defensive rebound percentage 25%, inverse estimated defensive rating 20%, defensive win shares/36 10%, PIE 10% |
| `stamina` | minutes/game 80%, total minutes 20% |
| `durability` | games played divided by scheduled games 100% |
| `overall` | PIE 35%, estimated net rating 20%, points/100 15%, minutes/game 12%, TS% 10%, availability 8% |

`impactPercentile` is the season-relative percentile of the overall composite. `overall` is mapped
from that percentile through the configured overall anchors. `talentTier` is derived only from the
configured overall ranges.

## Deferred attributes

Do not emit midrange shooting, shot creation, ball handling, help defense, speed, strength, foul
discipline, or detailed tendencies until a reviewed source and calculation supports them. ESPN
play-style data is expected to support some of these later, after source-ID reconciliation and
adapter work are complete.
