from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from player_generator.schema import RATING_FIELDS, TIER_ORDER


COMPARISON_RATINGS = (*RATING_FIELDS, "overall")
QUANTILES = (0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99)


def _distribution(frame: pd.DataFrame, field: str) -> dict[str, float]:
    values = pd.to_numeric(frame[field], errors="coerce").dropna()
    payload: dict[str, float] = {
        "mean": round(float(values.mean()), 3),
        "std": round(float(values.std(ddof=0)), 3),
        "min": round(float(values.min()), 3),
        "max": round(float(values.max()), 3),
    }
    for quantile in QUANTILES:
        payload[f"p{int(quantile * 100):02d}"] = round(float(values.quantile(quantile)), 3)
    return payload


def _category_distribution(frame: pd.DataFrame, field: str, order: list[str]) -> dict[str, Any]:
    counts = frame[field].value_counts().reindex(order, fill_value=0)
    total = max(int(counts.sum()), 1)
    return {
        key: {
            "count": int(value),
            "share": round(float(value) / total, 4),
        }
        for key, value in counts.items()
    }


def _correlation_distance(reference: pd.DataFrame, generated: pd.DataFrame) -> float:
    if len(reference) < 2 or len(generated) < 2:
        return 0.0
    reference_corr = reference[list(COMPARISON_RATINGS)].corr().to_numpy(dtype=float)
    generated_corr = generated[list(COMPARISON_RATINGS)].corr().to_numpy(dtype=float)
    mask = ~np.eye(len(COMPARISON_RATINGS), dtype=bool)
    difference = np.abs(reference_corr - generated_corr)[mask]
    finite = difference[np.isfinite(difference)]
    return round(float(finite.mean()), 4) if finite.size else 0.0


def _nearest_rating_distance(reference: pd.DataFrame, generated: pd.DataFrame) -> dict[str, float]:
    reference_matrix = reference[list(COMPARISON_RATINGS)].to_numpy(dtype=float)
    generated_matrix = generated[list(COMPARISON_RATINGS)].to_numpy(dtype=float)
    nearest: list[float] = []
    for row in generated_matrix:
        distances = np.mean(np.abs(reference_matrix - row), axis=1)
        nearest.append(float(np.min(distances)))
    values = np.asarray(nearest)
    return {
        "mean": round(float(values.mean()), 3),
        "median": round(float(np.median(values)), 3),
        "p10": round(float(np.quantile(values, 0.10)), 3),
        "minimum": round(float(values.min()), 3),
    }


def compare_rosters(
    reference: pd.DataFrame,
    generated: pd.DataFrame,
) -> tuple[dict[str, Any], pd.DataFrame]:
    missing_reference = [field for field in COMPARISON_RATINGS if field not in reference.columns]
    missing_generated = [field for field in COMPARISON_RATINGS if field not in generated.columns]
    if missing_reference or missing_generated:
        raise ValueError(
            f"Missing comparison fields. reference={missing_reference}, generated={missing_generated}"
        )

    rows: list[dict[str, Any]] = []
    rating_report: dict[str, Any] = {}
    warnings: list[str] = []
    for field in COMPARISON_RATINGS:
        ref_stats = _distribution(reference, field)
        gen_stats = _distribution(generated, field)
        quantile_errors = [
            abs(ref_stats[f"p{int(q * 100):02d}"] - gen_stats[f"p{int(q * 100):02d}"])
            for q in QUANTILES
        ]
        quantile_mae = round(float(np.mean(quantile_errors)), 3)
        mean_difference = round(gen_stats["mean"] - ref_stats["mean"], 3)
        std_difference = round(gen_stats["std"] - ref_stats["std"], 3)
        rating_report[field] = {
            "reference": ref_stats,
            "generated": gen_stats,
            "meanDifference": mean_difference,
            "stdDifference": std_difference,
            "quantileMAE": quantile_mae,
        }
        rows.append(
            {
                "rating": field,
                "reference_mean": ref_stats["mean"],
                "generated_mean": gen_stats["mean"],
                "mean_difference": mean_difference,
                "reference_std": ref_stats["std"],
                "generated_std": gen_stats["std"],
                "std_difference": std_difference,
                "quantile_mae": quantile_mae,
            }
        )
        if abs(mean_difference) > 4.0:
            warnings.append(f"{field}: generated mean differs by {mean_difference:+.1f} points.")
        if quantile_mae > 5.0:
            warnings.append(f"{field}: quantile error is {quantile_mae:.1f} points.")

    reference_names = {
        str(name).strip().casefold()
        for name in reference.get("sourcePlayerName", pd.Series(dtype=str)).dropna()
    }
    generated_names = {
        str(name).strip().casefold()
        for name in generated.get("displayName", pd.Series(dtype=str)).dropna()
    }
    name_collisions = sorted(reference_names & generated_names)

    reference_vectors = {
        tuple(int(value) for value in row)
        for row in reference[list(COMPARISON_RATINGS)].to_numpy()
    }
    exact_rating_matches = sum(
        tuple(int(value) for value in row) in reference_vectors
        for row in generated[list(COMPARISON_RATINGS)].to_numpy()
    )

    correlation_distance = _correlation_distance(reference, generated)
    if correlation_distance > 0.18:
        warnings.append(
            f"Rating correlation distance is {correlation_distance:.3f}; skill relationships may drift."
        )

    report = {
        "status": "pass" if not warnings and not name_collisions else "review",
        "referencePlayerCount": int(len(reference)),
        "generatedPlayerCount": int(len(generated)),
        "ratings": rating_report,
        "talentTiers": {
            "reference": _category_distribution(reference, "talentTier", list(TIER_ORDER)),
            "generated": _category_distribution(generated, "talentTier", list(TIER_ORDER)),
        },
        "positionGroups": {
            "reference": _category_distribution(
                reference, "positionGroup", ["guard", "wing", "big"]
            ),
            "generated": _category_distribution(
                generated, "positionGroup", ["guard", "wing", "big"]
            ),
        },
        "identityChecks": {
            "generatedNameCollisionsWithReference": len(name_collisions),
            "collidingNames": name_collisions,
            "exactFullRatingVectorMatches": int(exact_rating_matches),
            "nearestReferenceMeanAbsoluteRatingDistance": _nearest_rating_distance(
                reference, generated
            ),
        },
        "correlationMeanAbsoluteDifference": correlation_distance,
        "warnings": warnings,
    }
    return report, pd.DataFrame(rows)
