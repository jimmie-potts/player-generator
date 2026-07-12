# Starter rating model

The model is intentionally transparent and easy to replace.

## Processing order

1. Project the required totals, per-game, per-36, per-100, advanced and bio fields from the pinned
   `playerstats.parquet` snapshot.
2. Select end-season years 2021 through 2026 and players meeting the minutes threshold.
3. Infer broad guard/wing/big buckets from height and role metrics because the source has no position.
4. Stabilize 2P%, 3P% and FT% toward each season's league average.
5. Rank composite skill metrics within each season and interpolate them onto configured 25-99 curves.
6. Rank PIE, estimated net rating, points per 100, minutes, TS% and availability onto the overall
   curve.
7. Use all six rated seasons as the template pool, with recent seasons weighted more heavily, while
   retaining the latest season as the comparison snapshot.

## Inputs

- Shooting combines stabilized percentages with 2PA/3PA frequency and free-throw rate.
- Scoring combines points per 100 possessions, usage and true shooting.
- Playmaking uses assists per 36, assist percentage, assist ratio, assist-to-turnover and usage.
- Ball security uses inverse estimated turnover percentage, inverse turnovers per 100 and
  assist-to-turnover.
- Rebounding uses offensive and defensive rebound percentages.
- Defense uses steals or blocks per 100 with estimated defensive rating, defensive win shares, PIE
  and defensive rebound percentage.

## Why rank composites twice?

Each component is first converted to a percentile so metrics with different units can be combined.
The resulting weighted composite is ranked again. This ensures that the best composite performer
reaches the top of the configured scale even when no player is first in every component.

## Known limitations

- Per-36 and per-100 values do not fully account for role and opponent quality.
- Broad position groups are inferred, not authoritative source positions.
- Defensive rating, defensive win shares and PIE remain noisy individual-defense signals with team
  and context effects.
- Potential, detailed positions and development traits are synthetic game-design variables.
- ESPN play-style analytics are intentionally deferred.

Every formula and anchor is centralized in `ratings.py` and `config/default.yaml` so the simulator
can drive later tuning.
