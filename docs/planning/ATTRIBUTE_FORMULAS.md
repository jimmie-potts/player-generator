# Current player attribute formulas

Formula schema version 1 and active formula version `1.0.0` implement the initial explainable
player-attribute model. The structural contract is packaged as
`player_data_contracts/schemas/formula-v1.schema.json`; the active definition is packaged as
`player_attribute_engine/formulas/player-attributes-v1.json`.

## Output schema

```text
playerId,insideScoring,threePointShooting,freeThrowShooting,scoringVolume,playmaking,ballSecurity,offensiveRebounding,defensiveRebounding,perimeterDefense,interiorDefense,stamina,durability,overall,impactPercentile,talentTier,formulaVersion
```

Attributes use a 25–99 rating scale. Each component metric is converted to a season-relative
percentile, combined using normalized weights, ranked again where required, and mapped through
configurable percentile anchors. A component with direction `lower` treats lower raw values as
better.

Version `1.0.0` evaluates one season cohort per call. Every attribute requires at least 20 games,
500 minutes, a non-null season, and non-null component inputs. Missing or below-threshold rows are
excluded rather than imputed. Ties receive their average rank, ratings use half-even rounding after
linear interpolation, and lower-is-better components reverse only their percentile direction.

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

## Stabilization, schedules, and scales

For a shooting component, the engine calculates
`(made + leaguePercentage * priorAttempts) / (attempted + priorAttempts)`. The league percentage
uses all non-null rows in the season before formula eligibility is applied. Version `1.0.0` pins
priors of 150 two-point attempts, 100 three-point attempts, and 75 free-throw attempts. Availability
is games divided by the declared schedule and clipped to `0..1`; the schedule is 72 games for 2021
and 82 games for each season from 2022 through 2026. An unlisted season fails evaluation.

| Percentile | Skill rating | Overall rating |
|---:|---:|---:|
| 0.00 | 25 | 50 |
| 0.05 | 38 | 53 |
| 0.25 | 54 | 60 |
| 0.50 | 68 | 67 |
| 0.75 | 80 | 74 |
| 0.90 | 90 | 82 |
| 0.97 | interpolated | 89 |
| 0.98 | 97 | interpolated |
| 0.99 | interpolated | 94 |
| 1.00 | 99 | 97 |

Overall ratings `25–67`, `68–75`, `76–83`, `84–89`, and `90–99` map respectively to
`fringe`, `rotation`, `starter`, `all_star`, and `superstar`.

## Baseline calibration regressions

The ignored local 2026 reference cohort contains 376 eligible rows. Re-evaluating it with formula
version `1.0.0` reproduced the prior generated ratings without changing any output row:

- Jalen Duren's overall composite ranks 374th of 376, so `impactPercentile` is
  `0.9946808511`; the overall anchors map it to `95` and the versioned tier is `superstar`.
- Giannis Antetokounmpo's overall composite ranks 358th of 376, so `impactPercentile` is
  `0.9521276596`; the overall anchors map it to `87` and the versioned tier is `all_star`.

These results rank the declared season-relative composite, not a head-to-head judgment of every
basketball skill. In the prior baseline, the clearest counterintuitive separation was the 8%
availability component: Duren's availability percentile contribution was about `0.0566`, versus
about `0.0044` for Antetokounmpo. Synthetic tracked regressions preserve the two ranks and resulting
outputs without copying names, source IDs, or raw third-party rows into fixtures.

## Deferred attributes

Do not emit midrange shooting, shot creation, ball handling, help defense, speed, strength, foul
discipline, or detailed tendencies until a reviewed source and calculation supports them. ESPN
play-style data is expected to support some of these later, after source-ID reconciliation and
adapter work are complete.
