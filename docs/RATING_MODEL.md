# Starter rating model

The model is intentionally transparent and easy to replace.

## Processing order

1. Aggregate player game rows into player-season totals.
2. Convert counting statistics to per-36 rates.
3. Stabilize 2P%, 3P% and FT% toward each season's league average.
4. Rank composite skill metrics within the season.
5. Interpolate percentiles onto configurable 25-99 curves.
6. Rank an overall production composite onto a separate 50-97 curve.

## Why rank composites twice?

Each component is first converted to a percentile so metrics with different units can be combined.
The resulting weighted composite is ranked again. This ensures that the best composite performer
reaches the top of the configured scale even when no player is first in every component.

## Known limitations

- Per-36 values do not fully account for role and opponent quality.
- The box-score defensive ratings are placeholders.
- Plus-minus is noisy and is deliberately given a small weight.
- Height and weight coverage comes from a second historical index and is incomplete for some newer
  players.
- Potential, detailed positions and development traits are synthetic game-design variables.

Every formula and anchor is centralized in `ratings.py` and `config/default.yaml` so the simulator
can drive later tuning.
