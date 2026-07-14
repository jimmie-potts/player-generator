from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from faker import Faker
from player_attribute_engine import FormulaDocument, evaluate_player_attributes
from player_data_contracts import ROSTER_CONTRACT_VERSION

from roster_generator.config import configuration_hash
from roster_generator.reference_package import LoadedReferencePackage
from roster_generator.selection import (
    SelectionSettings,
    eligible_candidates,
    infer_template_possessions,
    select_templates,
)


class RosterGenerationError(ValueError):
    """Raised when validated inputs cannot produce a consistent roster package."""


@dataclass(frozen=True)
class MutationSettings:
    count_log_sigma: float
    shooting_percentage_sigma: float
    advanced_fraction_sigma: float
    advanced_rating_sigma: float
    age_sigma: float
    height_sigma: float
    weight_sigma: float

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> MutationSettings:
        expected = {
            "count_log_sigma",
            "shooting_percentage_sigma",
            "advanced_fraction_sigma",
            "advanced_rating_sigma",
            "age_sigma",
            "height_sigma",
            "weight_sigma",
        }
        missing = expected - set(value)
        unknown = set(value) - expected
        if missing or unknown:
            details: list[str] = []
            if missing:
                details.append(f"missing keys: {', '.join(sorted(missing))}")
            if unknown:
                details.append(f"unknown keys: {', '.join(sorted(unknown))}")
            raise RosterGenerationError(f"Invalid mutation configuration ({'; '.join(details)})")

        parsed: dict[str, float] = {}
        for key in sorted(expected):
            raw = value[key]
            if isinstance(raw, bool) or not isinstance(raw, (int, float)):
                raise RosterGenerationError(f"mutation.{key} must be a finite nonnegative number")
            number = float(raw)
            if not math.isfinite(number) or number < 0:
                raise RosterGenerationError(f"mutation.{key} must be a finite nonnegative number")
            parsed[key] = number
        return cls(**parsed)


@dataclass(frozen=True)
class GeneratedRoster:
    tables: Mapping[str, list[dict[str, object]]]
    seed: int
    configuration_hash: str


def _optional_number(row: Mapping[str, object], field: str) -> float | None:
    value = row.get(field)
    if value is None or pd.isna(value):
        return None
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _required_positive(row: Mapping[str, object], field: str) -> float:
    value = _optional_number(row, field)
    if value is None or value <= 0:
        raise RosterGenerationError(
            f"Selected reference template has no positive {field}; validation stopped generation"
        )
    return value


def _rounded(value: float, digits: int = 8) -> float:
    return round(float(value), digits)


def _ratio(
    numerator: float | int | None,
    denominator: float | int | None,
    scale: float = 1.0,
) -> float | None:
    if numerator is None or denominator is None or float(denominator) <= 0:
        return None
    return _rounded(float(numerator) / float(denominator) * scale)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _mutate_optional_int(
    row: Mapping[str, object],
    field: str,
    sigma: float,
    minimum: int,
    maximum: int,
    rng: np.random.Generator,
) -> int | None:
    value = _optional_number(row, field)
    if value is None:
        return None
    return int(round(_clamp(value + float(rng.normal(0.0, sigma)), minimum, maximum)))


def _mutate_count(
    source: float | None,
    volume_multiplier: float,
    sigma: float,
    rng: np.random.Generator,
) -> int | None:
    if source is None:
        return None
    event_multiplier = float(np.exp(rng.normal(0.0, sigma)))
    return max(0, int(round(source * volume_multiplier * event_multiplier)))


def _mutated_makes(
    source_makes: float | None,
    source_attempts: float | None,
    attempts: int,
    sigma: float,
    rng: np.random.Generator,
) -> int:
    if source_makes is None or source_attempts is None:
        raise RosterGenerationError(
            "Selected reference template lacks a shooting make/attempt pair"
        )
    if source_makes < 0 or source_attempts < 0 or source_makes > source_attempts:
        raise RosterGenerationError(
            "Selected reference template has an invalid shooting make/attempt pair"
        )
    if source_attempts == 0:
        return 0
    percentage = _clamp(
        source_makes / source_attempts + float(rng.normal(0.0, sigma)),
        0.0,
        1.0,
    )
    return min(attempts, max(0, int(round(attempts * percentage))))


def _infer_possessions(row: Mapping[str, object]) -> float:
    inferred = infer_template_possessions(row)
    if inferred is None:
        raise RosterGenerationError(
            "Selected reference template has no usable total/per-100 pair for possession inference"
        )
    return inferred


def _reference_count(
    row: Mapping[str, object],
    total_field: str,
    *,
    per36_field: str | None,
    per100_field: str | None,
    minutes: float,
    possessions: float,
) -> float | None:
    total = _optional_number(row, total_field)
    if total is not None:
        return total
    if per36_field is not None:
        per36 = _optional_number(row, per36_field)
        if per36 is not None:
            return per36 * minutes / 36.0
    if per100_field is not None:
        per100 = _optional_number(row, per100_field)
        if per100 is not None:
            return per100 * possessions / 100.0
    return None


def _mutate_stats(
    template: Mapping[str, object],
    player_id: str,
    settings: MutationSettings,
    rng: np.random.Generator,
) -> dict[str, object]:
    season = int(round(_required_positive(template, "season")))
    games = int(round(_required_positive(template, "games")))
    minutes = _rounded(_required_positive(template, "minutes"))
    reference_possessions = _infer_possessions(template)
    volume_multiplier = float(
        np.clip(np.exp(rng.normal(0.0, settings.count_log_sigma)), 0.75, 1.25)
    )

    source_three_attempts = _optional_number(template, "threePointersAttempted")
    source_three_makes = _optional_number(template, "threePointersMade")
    source_two_attempts = _optional_number(template, "twoPointersAttempted")
    source_two_makes = _optional_number(template, "twoPointersMade")
    source_free_attempts = _optional_number(template, "freeThrowsAttempted")
    source_free_makes = _optional_number(template, "freeThrowsMade")
    if any(
        value is None
        for value in (
            source_three_attempts,
            source_three_makes,
            source_two_attempts,
            source_two_makes,
            source_free_attempts,
            source_free_makes,
        )
    ):
        raise RosterGenerationError("Selected reference template lacks required shooting totals")

    two_attempts = max(0, int(round(float(source_two_attempts) * volume_multiplier)))
    three_attempts = max(0, int(round(float(source_three_attempts) * volume_multiplier)))
    free_attempts = max(0, int(round(float(source_free_attempts) * volume_multiplier)))
    two_makes = _mutated_makes(
        source_two_makes,
        source_two_attempts,
        two_attempts,
        settings.shooting_percentage_sigma,
        rng,
    )
    three_makes = _mutated_makes(
        source_three_makes,
        source_three_attempts,
        three_attempts,
        settings.shooting_percentage_sigma,
        rng,
    )
    free_makes = _mutated_makes(
        source_free_makes,
        source_free_attempts,
        free_attempts,
        settings.shooting_percentage_sigma,
        rng,
    )

    field_goal_attempts = two_attempts + three_attempts
    field_goal_makes = two_makes + three_makes
    points = 2 * two_makes + 3 * three_makes + free_makes
    rebounds_offensive = _mutate_count(
        _reference_count(
            template,
            "reboundsOffensive",
            per36_field="offensiveReboundsPer36",
            per100_field=None,
            minutes=minutes,
            possessions=reference_possessions,
        ),
        volume_multiplier,
        settings.count_log_sigma,
        rng,
    )
    rebounds_defensive = _mutate_count(
        _reference_count(
            template,
            "reboundsDefensive",
            per36_field="defensiveReboundsPer36",
            per100_field=None,
            minutes=minutes,
            possessions=reference_possessions,
        ),
        volume_multiplier,
        settings.count_log_sigma,
        rng,
    )
    rebounds_total = (
        rebounds_offensive + rebounds_defensive
        if rebounds_offensive is not None and rebounds_defensive is not None
        else None
    )
    event_totals: dict[str, int | None] = {}
    for field, per36_field, per100_field in (
        ("assists", "assistsPer36", "assistsPer100"),
        ("turnovers", "turnoversPer36", "turnoversPer100"),
        ("steals", "stealsPer36", "stealsPer100"),
        ("blocks", "blocksPer36", "blocksPer100"),
        ("foulsPersonal", None, None),
    ):
        event_totals[field] = _mutate_count(
            _reference_count(
                template,
                field,
                per36_field=per36_field,
                per100_field=per100_field,
                minutes=minutes,
                possessions=reference_possessions,
            ),
            volume_multiplier,
            settings.count_log_sigma,
            rng,
        )
    assists = event_totals["assists"]
    turnovers = event_totals["turnovers"]
    steals = event_totals["steals"]
    blocks = event_totals["blocks"]
    fouls = event_totals["foulsPersonal"]
    if any(value is None for value in (assists, turnovers, steals, blocks)):
        raise RosterGenerationError(
            "Selected reference template lacks a usable total or rate for a required event stat"
        )
    source_plus_minus = _reference_count(
        template,
        "plusMinusPoints",
        per36_field="plusMinusPer36",
        per100_field=None,
        minutes=minutes,
        possessions=reference_possessions,
    )
    plus_minus = (
        None
        if source_plus_minus is None
        else int(round(source_plus_minus * volume_multiplier + rng.normal(0.0, 8.0)))
    )
    possessions = _rounded(max(1.0, reference_possessions * volume_multiplier))

    return {
        "playerId": player_id,
        "season": season,
        "games": games,
        "minutes": minutes,
        "possessions": possessions,
        "fieldGoalsMade": field_goal_makes,
        "fieldGoalsAttempted": field_goal_attempts,
        "twoPointersMade": two_makes,
        "twoPointersAttempted": two_attempts,
        "threePointersMade": three_makes,
        "threePointersAttempted": three_attempts,
        "freeThrowsMade": free_makes,
        "freeThrowsAttempted": free_attempts,
        "reboundsOffensive": rebounds_offensive,
        "reboundsDefensive": rebounds_defensive,
        "reboundsTotal": rebounds_total,
        "assists": assists,
        "turnovers": turnovers,
        "steals": steals,
        "blocks": blocks,
        "foulsPersonal": fouls,
        "points": points,
        "plusMinusPoints": plus_minus,
        "fieldGoalPercentage": _ratio(field_goal_makes, field_goal_attempts),
        "twoPointPercentage": _ratio(two_makes, two_attempts),
        "threePointPercentage": _ratio(three_makes, three_attempts),
        "freeThrowPercentage": _ratio(free_makes, free_attempts),
        "minutesPerGame": _ratio(minutes, games),
        "pointsPerGame": _ratio(points, games),
        "reboundsPerGame": _ratio(rebounds_total, games),
        "assistsPerGame": _ratio(assists, games),
        "turnoversPerGame": _ratio(turnovers, games),
        "threePointAttemptsPer36": _ratio(three_attempts, minutes, 36.0),
        "freeThrowAttemptsPer36": _ratio(free_attempts, minutes, 36.0),
        "offensiveReboundsPer36": _ratio(rebounds_offensive, minutes, 36.0),
        "defensiveReboundsPer36": _ratio(rebounds_defensive, minutes, 36.0),
        "assistsPer36": _ratio(assists, minutes, 36.0),
        "turnoversPer36": _ratio(turnovers, minutes, 36.0),
        "stealsPer36": _ratio(steals, minutes, 36.0),
        "blocksPer36": _ratio(blocks, minutes, 36.0),
        "pointsPer36": _ratio(points, minutes, 36.0),
        "plusMinusPer36": _ratio(plus_minus, minutes, 36.0),
        "pointsPer100": _ratio(points, possessions, 100.0),
        "assistsPer100": _ratio(assists, possessions, 100.0),
        "turnoversPer100": _ratio(turnovers, possessions, 100.0),
        "stealsPer100": _ratio(steals, possessions, 100.0),
        "blocksPer100": _ratio(blocks, possessions, 100.0),
        "twoPointAttemptFrequency": _ratio(two_attempts, field_goal_attempts),
        "threePointAttemptFrequency": _ratio(three_attempts, field_goal_attempts),
    }


def _mutate_fraction(
    template: Mapping[str, object],
    field: str,
    sigma: float,
    rng: np.random.Generator,
) -> float | None:
    source = _optional_number(template, field)
    if source is None:
        return None
    return _rounded(_clamp(source + float(rng.normal(0.0, sigma)), 0.0, 1.0))


def _mutate_rating(
    template: Mapping[str, object],
    field: str,
    sigma: float,
    rng: np.random.Generator,
) -> float | None:
    source = _optional_number(template, field)
    if source is None:
        return None
    return _rounded(_clamp(source + float(rng.normal(0.0, sigma)), 0.0, 200.0))


def _mutate_advanced(
    template: Mapping[str, object],
    stats: Mapping[str, object],
    settings: MutationSettings,
    rng: np.random.Generator,
) -> dict[str, object]:
    estimated_offense = _mutate_rating(
        template, "estimatedOffensiveRating", settings.advanced_rating_sigma, rng
    )
    offense = _mutate_rating(template, "offensiveRating", settings.advanced_rating_sigma, rng)
    estimated_defense = _mutate_rating(
        template, "estimatedDefensiveRating", settings.advanced_rating_sigma, rng
    )
    defense = _mutate_rating(template, "defensiveRating", settings.advanced_rating_sigma, rng)
    offensive_rebound_percentage = _mutate_fraction(
        template, "offensiveReboundPercentage", settings.advanced_fraction_sigma, rng
    )
    defensive_rebound_percentage = _mutate_fraction(
        template, "defensiveReboundPercentage", settings.advanced_fraction_sigma, rng
    )
    assists = stats["assists"]
    turnovers = stats["turnovers"]
    field_goal_attempts = stats["fieldGoalsAttempted"]
    field_goal_makes = stats["fieldGoalsMade"]
    three_point_makes = stats["threePointersMade"]
    free_throw_attempts = stats["freeThrowsAttempted"]
    points = stats["points"]
    minutes = stats["minutes"]
    defensive_win_shares = _optional_number(template, "defensiveWinShares")
    if defensive_win_shares is not None:
        defensive_win_shares = _rounded(
            defensive_win_shares
            + float(rng.normal(0.0, max(0.05, abs(defensive_win_shares) * 0.08)))
        )

    true_shooting_denominator = (
        2.0 * (float(field_goal_attempts) + 0.44 * float(free_throw_attempts))
    )
    play_ending_denominator = (
        float(field_goal_attempts)
        + 0.44 * float(free_throw_attempts)
        + float(assists)
        + float(turnovers)
    )
    return {
        "playerId": stats["playerId"],
        "season": stats["season"],
        "estimatedOffensiveRating": estimated_offense,
        "offensiveRating": offense,
        "estimatedDefensiveRating": estimated_defense,
        "defensiveRating": defense,
        "estimatedNetRating": (
            None
            if estimated_offense is None or estimated_defense is None
            else _rounded(estimated_offense - estimated_defense)
        ),
        "netRating": (
            None if offense is None or defense is None else _rounded(offense - defense)
        ),
        "assistPercentage": _mutate_fraction(
            template, "assistPercentage", settings.advanced_fraction_sigma, rng
        ),
        "assistTurnoverRatio": _ratio(assists, max(float(turnovers), 1.0)),
        "assistRatio": _ratio(assists, play_ending_denominator, 100.0),
        "offensiveReboundPercentage": offensive_rebound_percentage,
        "defensiveReboundPercentage": defensive_rebound_percentage,
        "reboundPercentage": _mutate_fraction(
            template, "reboundPercentage", settings.advanced_fraction_sigma, rng
        ),
        "estimatedTurnoverPercentage": _ratio(
            turnovers, play_ending_denominator, 100.0
        ),
        "effectiveFieldGoalPercentage": _ratio(
            float(field_goal_makes) + 0.5 * float(three_point_makes),
            field_goal_attempts,
        ),
        "trueShootingPercentage": _ratio(points, true_shooting_denominator),
        "usagePercentage": _mutate_fraction(
            template, "usagePercentage", settings.advanced_fraction_sigma, rng
        ),
        "playerImpactEstimate": _mutate_fraction(
            template, "playerImpactEstimate", settings.advanced_fraction_sigma, rng
        ),
        "defensiveWinShares": defensive_win_shares,
        "defensiveWinSharesPer36": _ratio(defensive_win_shares, minutes, 36.0),
    }


def _player_id(seed: int, ordinal: int) -> str:
    value = f"roster-v1:{seed}:{ordinal}".encode()
    return f"player_{hashlib.sha256(value).hexdigest()[:16]}"


def _unique_name(
    faker: Faker,
    forbidden_names: frozenset[str],
    used_names: set[str],
) -> tuple[str, str]:
    for _ in range(500):
        first_name = faker.first_name_male()
        last_name = faker.last_name()
        normalized = f"{first_name} {last_name}".strip().casefold()
        if normalized not in forbidden_names and normalized not in used_names:
            used_names.add(normalized)
            return first_name, last_name
    raise RosterGenerationError("Unable to generate a unique roster player name")


def _evaluate_attributes(
    stats_rows: list[dict[str, object]],
    advanced_rows: list[dict[str, object]],
    formula: FormulaDocument,
) -> list[dict[str, object]]:
    stats = pd.DataFrame(stats_rows)
    advanced = pd.DataFrame(advanced_rows)
    frame = stats.merge(advanced, on=["playerId", "season"], how="inner", validate="one_to_one")
    evaluated_by_position: dict[int, dict[str, object]] = {}
    for _season, indices in frame.groupby("season", sort=True).groups.items():
        positions = [int(index) for index in indices]
        batch = evaluate_player_attributes(frame.loc[positions].reset_index(drop=True), formula)
        for offset, position in enumerate(positions):
            row = dict(batch.rows[offset])
            if any(row[field] is None for field in formula.output_fields):
                raise RosterGenerationError(
                    "Generated statistics produced an incomplete attribute row; no package written"
                )
            evaluated_by_position[position] = row
    if len(evaluated_by_position) != len(frame):
        raise RosterGenerationError("Generated attribute evaluation did not cover every player")
    return [evaluated_by_position[position] for position in range(len(frame))]


def generate_roster_tables(
    package: LoadedReferencePackage,
    formula: FormulaDocument,
    config: Mapping[str, Any],
    *,
    seed: int | None = None,
) -> GeneratedRoster:
    generation = config.get("generation")
    project = config.get("project")
    mutation = config.get("mutation")
    selection = config.get("selection")
    if not isinstance(project, Mapping) or set(project) != {"roster_contract_version"}:
        raise RosterGenerationError(
            "project must contain exactly the roster_contract_version setting"
        )
    contract_version = project["roster_contract_version"]
    if isinstance(contract_version, bool) or not isinstance(contract_version, int):
        raise RosterGenerationError("project.roster_contract_version must be an integer")
    if contract_version != ROSTER_CONTRACT_VERSION:
        raise RosterGenerationError(
            "Unsupported configured roster contract version "
            f"{contract_version}; supported version is {ROSTER_CONTRACT_VERSION}"
        )
    if not isinstance(generation, Mapping) or set(generation) != {"seed"}:
        raise RosterGenerationError("generation must contain exactly the seed setting")
    raw_seed = generation["seed"] if seed is None else seed
    if isinstance(raw_seed, bool) or not isinstance(raw_seed, int):
        raise RosterGenerationError("generation.seed must be an integer")
    if not isinstance(mutation, Mapping):
        raise RosterGenerationError("mutation must be a mapping")
    if not isinstance(selection, Mapping):
        raise RosterGenerationError("selection must be a mapping")

    actual_seed = int(raw_seed)
    mutation_settings = MutationSettings.from_mapping(mutation)
    selection_settings = SelectionSettings.from_mapping(selection)
    rng = np.random.default_rng(actual_seed)
    candidates = eligible_candidates(package, formula, selection_settings)
    templates = select_templates(candidates, selection_settings, rng)

    faker = Faker("en_US")
    faker.seed_instance(actual_seed)
    used_names: set[str] = set()
    players: list[dict[str, object]] = []
    stats_rows: list[dict[str, object]] = []
    advanced_rows: list[dict[str, object]] = []
    for ordinal, raw_template in enumerate(templates.to_dict(orient="records"), start=1):
        player_id = _player_id(actual_seed, ordinal)
        first_name, last_name = _unique_name(
            faker, package.forbidden_names, used_names
        )
        players.append(
            {
                "playerId": player_id,
                "displayName": f"{first_name} {last_name}",
                "firstName": first_name,
                "lastName": last_name,
                "age": _mutate_optional_int(
                    raw_template, "age", mutation_settings.age_sigma, 18, 45, rng
                ),
                "heightInches": _mutate_optional_int(
                    raw_template,
                    "heightInches",
                    mutation_settings.height_sigma,
                    60,
                    96,
                    rng,
                ),
                "weightPounds": _mutate_optional_int(
                    raw_template,
                    "weightPounds",
                    mutation_settings.weight_sigma,
                    140,
                    350,
                    rng,
                ),
            }
        )
        stats = _mutate_stats(raw_template, player_id, mutation_settings, rng)
        stats_rows.append(stats)
        advanced_rows.append(_mutate_advanced(raw_template, stats, mutation_settings, rng))

    attributes = _evaluate_attributes(stats_rows, advanced_rows, formula)
    return GeneratedRoster(
        tables={
            "players.csv": players,
            "player_stats.csv": stats_rows,
            "player_advanced_stats.csv": advanced_rows,
            "player_attributes.csv": attributes,
        },
        seed=actual_seed,
        configuration_hash=configuration_hash(config, actual_seed),
    )
