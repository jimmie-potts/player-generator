# Current declarative rating model

Formula schema version 1 and active formula version `1.0.0` make the player-attribute calculation
inspectable and reproducible. The machine-readable structure is owned by `data-contracts`; the
active formula and evaluator are owned by `attribute-engine`.

## Processing order

1. Accept already joined, camelCase player-season metrics. The engine has no source adapter, file,
   package, or application-configuration dependency. Numeric strings, booleans, complex values,
   and temporal values are rejected rather than coerced into formula inputs.
2. Derive only formula-declared ratios, stabilized shooting percentages, and scheduled-game ratios.
   Shooting league averages use every row in the season before player eligibility is applied.
3. Exclude a player from an attribute when a required value is null or its versioned minimum of 20
   games and 500 minutes is not met.
4. Rank every component inside its declared season cohort. Ties receive their average rank; inverse
   components rank lower values as better.
5. Multiply component percentiles by normalized weights and sum the contributions. The active
   formulas rank that composite again inside the same eligible season cohort.
6. Interpolate the composite percentile through the attribute's declared 25–99 anchors, round
   half-even, and clamp to the output scale.
7. Use the overall composite percentile as `impactPercentile`, map it through the overall anchors,
   and assign `talentTier` only from the formula's versioned overall ranges.

Pandas `rank(method="average", pct=True)` is the versioned percentile definition. Its minimum rank
is `1 / cohort size`, its maximum is `1.0`, and an eligible singleton receives `1.0`. Nulls are never
median-filled; an excluded player receives empty attribute outputs plus structured reasons.

## Formula inputs

- Inside scoring combines stabilized 2P%, 2PA frequency, and free-throw rate.
- Three-point and free-throw shooting use stabilized percentages with declared priors of 100 and 75
  attempts; 2P% uses 150.
- Scoring combines points per 100 possessions, usage, and true shooting.
- Playmaking uses assist percentage, assists per 36, assist ratio, assist-to-turnover ratio, and
  usage.
- Ball security uses inverse estimated turnover percentage, assist-to-turnover ratio, and inverse
  turnovers per 100.
- Rebounding uses offensive and defensive rebound percentages.
- Defense uses steals or blocks per 100 with inverse estimated defensive rating, defensive win
  shares per 36, PIE, and defensive rebound percentage.
- Stamina combines minutes per game and total minutes. Durability uses games divided by the
  versioned scheduled-game count, clipped to `0..1`.
- Overall combines PIE, estimated net rating, points per 100, minutes per game, true shooting, and
  availability.

The active resource pins scheduled games under canonical four-digit end-season keys for 2021
through 2026. An unlisted season fails before evaluation instead of silently assuming a schedule.

## Explanation contract

Each evaluated attribute returns raw component values, component percentiles, normalized weights,
contributions, their weighted composite, the composite percentile, final rating, cohort identity,
eligible cohort size, and any ineligibility reasons. These values are JSON-serializable and are the
single calculation detail batch and preview consumers use. The version 1 preview API returns the
same explanation for baseline and temporary request-local calculations; it does not reconstruct the
formula in its HTTP layer.

Preview rank is a presentation value separate from formula percentile evaluation. It ranks overall
ratings across the same complete configured season cohort with minimum-rank ties, while the formula
continues to use its declared average-rank percentile semantics for components and composites.

## Known limitations

- Per-36 and per-100 metrics do not fully account for role and opponent quality.
- Defensive rating, defensive win shares, and PIE remain noisy individual-defense signals with team
  and context effects.
- The current formula supports only the attributes listed in
  [ATTRIBUTE_FORMULAS.md](planning/ATTRIBUTE_FORMULAS.md). Unsupported play-style, physical, and
  tendency attributes are absent rather than filled with placeholders.
- The standalone wide reference build remains a legacy compatibility consumer. Normalized reference
  publication, normalized roster generation, and the formula preview API evaluate their respective
  complete season cohorts through the same formula engine.
