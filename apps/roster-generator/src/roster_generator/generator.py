from __future__ import annotations

from datetime import date
from typing import Any

import numpy as np
import pandas as pd
from faker import Faker
from player_data_contracts.models import RATING_FIELDS, TIER_ORDER

from roster_generator.models import POSITION_GROUPS
from roster_generator.teams import TEAMS


def _clamp_int(value: float, minimum: int = 25, maximum: int = 99) -> int:
    return int(max(minimum, min(maximum, round(float(value)))))


def _expanded_targets(targets: dict[str, int], order: tuple[str, ...]) -> list[str]:
    labels: list[str] = []
    for key in order:
        labels.extend([key] * int(targets.get(key, 0)))
    return labels


def _validate_targets(config: dict[str, Any]) -> int:
    generation = config["league_generation"]
    total_players = int(generation["team_count"]) * int(generation["roster_size"])
    talent_total = sum(int(value) for value in generation["talent_targets"].values())
    position_total = sum(int(value) for value in generation["position_targets"].values())
    if talent_total != total_players:
        raise ValueError(f"Talent targets total {talent_total}; expected {total_players}.")
    if position_total != total_players:
        raise ValueError(f"Position targets total {position_total}; expected {total_players}.")
    if int(generation["team_count"]) > len(TEAMS):
        raise ValueError(f"Only {len(TEAMS)} team definitions are available.")
    return total_players


def _sample_template(
    reference: pd.DataFrame,
    tier: str,
    position_group: str,
    rng: np.random.Generator,
) -> pd.Series:
    candidates = reference[
        (reference["talentTier"] == tier) & (reference["positionGroup"] == position_group)
    ]
    if candidates.empty:
        candidates = reference[reference["talentTier"] == tier]
    if candidates.empty:
        candidates = reference[reference["positionGroup"] == position_group]
    if candidates.empty:
        candidates = reference

    minute_weights = np.sqrt(pd.to_numeric(candidates["minutes"], errors="coerce").fillna(1.0))
    if "seasonWeight" in candidates:
        season_weights = pd.to_numeric(candidates["seasonWeight"], errors="coerce").fillna(1.0)
    else:
        season_weights = pd.Series(1.0, index=candidates.index)
    probabilities = (minute_weights * season_weights).to_numpy(dtype=float)
    probabilities = probabilities / probabilities.sum()
    chosen_index = rng.choice(candidates.index.to_numpy(), p=probabilities)
    return reference.loc[chosen_index]


def _mutate_ratings(
    template: pd.Series,
    tier: str,
    config: dict[str, Any],
    rng: np.random.Generator,
) -> dict[str, int]:
    minimum = int(config["ratings"]["minimum"])
    maximum = int(config["ratings"]["maximum"])
    volatility = config["ratings"]["volatility"]

    ratings: dict[str, int] = {}
    deltas: list[float] = []
    for field in RATING_FIELDS:
        source = float(template[field])
        mutated = source + rng.normal(0.0, float(volatility[field]))
        ratings[field] = _clamp_int(mutated, minimum, maximum)
        deltas.append(ratings[field] - source)

    overall_base = float(template["overall"])
    overall = overall_base + 0.18 * float(np.mean(deltas)) + rng.normal(0.0, 1.25)
    low, high = config["league_generation"]["tier_bounds"][tier]
    ratings["overall"] = _clamp_int(overall, int(low), int(high))
    return ratings


def _generate_age(tier: str, overall: int, rng: np.random.Generator) -> int:
    means = {
        "superstar": 28.0,
        "all_star": 27.0,
        "starter": 26.0,
        "rotation": 25.5,
        "fringe": 24.5,
    }
    standard_deviation = 3.7 if tier in {"superstar", "all_star"} else 4.4
    age = int(round(rng.normal(means[tier], standard_deviation)))
    if overall >= 90:
        return max(22, min(35, age))
    return max(19, min(36, age))


def _generate_potential(age: int, overall: int, rng: np.random.Generator) -> int:
    if age <= 21:
        growth = rng.integers(5, 17)
    elif age <= 24:
        growth = rng.integers(2, 12)
    elif age <= 27:
        growth = rng.integers(0, 7)
    elif age <= 30:
        growth = rng.integers(0, 4)
    else:
        growth = rng.integers(0, 2)
    return _clamp_int(overall + int(growth), overall, 99)


def _physical_profile(
    template: pd.Series,
    position_group: str,
    config: dict[str, Any],
    rng: np.random.Generator,
) -> tuple[int, int]:
    profile = config["league_generation"]["physical_profiles"][position_group]
    base_height = float(profile["height_mean"])
    template_height = pd.to_numeric(template.get("heightInches"), errors="coerce")
    if pd.notna(template_height):
        base_height = 0.35 * float(template_height) + 0.65 * base_height
    height = int(round(rng.normal(base_height, float(profile["height_std"]))))

    base_weight = float(profile["weight_mean"])
    template_weight = pd.to_numeric(template.get("weightPounds"), errors="coerce")
    if pd.notna(template_weight):
        base_weight = 0.30 * float(template_weight) + 0.70 * base_weight
    weight = int(round(rng.normal(base_weight, float(profile["weight_std"]))))

    height_limits = {"guard": (69, 80), "wing": (74, 84), "big": (78, 88)}
    weight_limits = {"guard": (160, 240), "wing": (185, 270), "big": (210, 310)}
    height = max(height_limits[position_group][0], min(height_limits[position_group][1], height))
    weight = max(weight_limits[position_group][0], min(weight_limits[position_group][1], weight))
    return height, weight


def _positions(position_group: str, ratings: dict[str, int]) -> tuple[str, str | None]:
    if position_group == "guard":
        if ratings["playmaking"] >= ratings["scoringVolume"] - 2:
            return "PG", "SG"
        return "SG", "PG" if ratings["playmaking"] >= 68 else "SF"
    if position_group == "wing":
        frontcourt_score = ratings["insideScoring"] + ratings["defensiveRebounding"]
        if frontcourt_score >= 148:
            return "PF", "SF"
        return "SF", "SG" if ratings["perimeterDefense"] >= 65 else "PF"
    anchor_score = ratings["interiorDefense"] + ratings["defensiveRebounding"]
    if anchor_score >= 145:
        return "C", "PF"
    return "PF", "C"


def _archetype(position_group: str, ratings: dict[str, int]) -> str:
    if ratings["perimeterDefense"] >= 82 and ratings["threePointShooting"] >= 78:
        return "Three-and-D Specialist"
    if ratings["interiorDefense"] >= 84 and ratings["defensiveRebounding"] >= 80:
        return "Defensive Anchor"
    if ratings["playmaking"] >= 84 and ratings["scoringVolume"] >= 78:
        return "Lead Creator"
    if ratings["threePointShooting"] >= 86:
        return "Floor Spacer"
    if ratings["insideScoring"] >= 84 and position_group == "big":
        return "Interior Finisher"
    if ratings["offensiveRebounding"] >= 84:
        return "Glass Cleaner"
    if ratings["scoringVolume"] >= 84:
        return "Primary Scorer"
    if ratings["perimeterDefense"] >= 80 or ratings["interiorDefense"] >= 80:
        return "Defensive Specialist"
    if position_group == "guard" and ratings["playmaking"] >= 75:
        return "Table Setter"
    if position_group == "wing":
        return "Versatile Wing"
    if position_group == "big":
        return "Two-Way Big"
    return "Balanced Guard"


def _unique_name(
    faker: Faker,
    forbidden_names: set[str],
    used_names: set[str],
) -> tuple[str, str]:
    for _ in range(500):
        first = faker.first_name_male()
        last = faker.last_name()
        full = f"{first} {last}".strip()
        normalized = full.casefold()
        if normalized not in forbidden_names and normalized not in used_names:
            used_names.add(normalized)
            return first, last
    raise RuntimeError("Unable to generate a unique roster player name.")


def _assign_teams(
    players: list[dict[str, Any]],
    config: dict[str, Any],
    rng: np.random.Generator,
) -> list[dict[str, Any]]:
    team_count = int(config["league_generation"]["team_count"])
    teams = list(TEAMS[:team_count])
    per_team_targets = config["league_generation"]["roster_position_targets"]

    player_by_id = {player["id"]: player for player in players}
    roster_ids: dict[str, list[str]] = {team.team_id: [] for team in teams}
    group_counts: dict[str, dict[str, int]] = {
        team.team_id: {group: 0 for group in POSITION_GROUPS} for team in teams
    }
    strength = {team.team_id: 0 for team in teams}
    premium_count = {team.team_id: 0 for team in teams}
    tiebreak = {team.team_id: float(rng.random()) for team in teams}

    ordered_players = sorted(
        players,
        key=lambda player: (
            player["ratings"]["overall"],
            player["ratings"]["potential"],
        ),
        reverse=True,
    )
    for player in ordered_players:
        group = player["positionGroup"]
        candidates = [
            team
            for team in teams
            if group_counts[team.team_id][group] < int(per_team_targets[group])
        ]
        if not candidates:
            raise ValueError(f"No remaining team slot for position group {group}.")
        chosen = min(
            candidates,
            key=lambda team: (
                strength[team.team_id],
                premium_count[team.team_id],
                len(roster_ids[team.team_id]),
                tiebreak[team.team_id],
            ),
        )
        team_id = chosen.team_id
        player["teamId"] = team_id
        roster_ids[team_id].append(player["id"])
        group_counts[team_id][group] += 1
        strength[team_id] += int(player["ratings"]["overall"])
        if player["talentTier"] in {"superstar", "all_star"}:
            premium_count[team_id] += 1

    team_payloads: list[dict[str, Any]] = []
    for team in teams:
        roster = sorted(
            (player_by_id[player_id] for player_id in roster_ids[team.team_id]),
            key=lambda player: player["ratings"]["overall"],
            reverse=True,
        )
        expected_size = sum(int(value) for value in per_team_targets.values())
        if len(roster) != expected_size:
            raise AssertionError(
                f"{team.team_id} has {len(roster)} players; expected {expected_size}."
            )
        for group in POSITION_GROUPS:
            expected = int(per_team_targets[group])
            actual = group_counts[team.team_id][group]
            if actual != expected:
                raise AssertionError(
                    f"{team.team_id} has {actual} {group}s; expected {expected}."
                )

        jersey_numbers = list(range(0, 100))
        rng.shuffle(jersey_numbers)
        for player, jersey in zip(roster, jersey_numbers, strict=False):
            player["jerseyNumber"] = int(jersey)
        team_payloads.append(
            {
                "id": team.team_id,
                "city": team.city,
                "nickname": team.nickname,
                "name": team.full_name,
                "abbreviation": team.abbreviation,
                "conference": team.conference,
                "roster": [player["id"] for player in roster],
                "averageOverall": round(
                    float(np.mean([player["ratings"]["overall"] for player in roster])), 2
                ),
            }
        )
    return team_payloads


def generate_league(
    reference: pd.DataFrame,
    config: dict[str, Any],
    seed: int | None = None,
) -> tuple[dict[str, Any], pd.DataFrame]:
    total_players = _validate_targets(config)
    actual_seed = int(seed if seed is not None else config["league_generation"]["seed"])
    rng = np.random.default_rng(actual_seed)
    faker = Faker("en_US")
    faker.seed_instance(actual_seed)

    talent_labels = _expanded_targets(config["league_generation"]["talent_targets"], TIER_ORDER)
    position_labels = _expanded_targets(
        config["league_generation"]["position_targets"], POSITION_GROUPS
    )
    rng.shuffle(talent_labels)
    rng.shuffle(position_labels)

    source_name_column = (
        "sourcePlayerName" if "sourcePlayerName" in reference else "personName"
    )
    forbidden_names = {
        str(value).strip().casefold()
        for value in reference[source_name_column].dropna().astype(str)
    }
    used_names: set[str] = set()
    players: list[dict[str, Any]] = []

    for index, (tier, position_group) in enumerate(
        zip(talent_labels, position_labels, strict=True), start=1
    ):
        template = _sample_template(reference, tier, position_group, rng)
        ratings = _mutate_ratings(template, tier, config, rng)
        age = _generate_age(tier, ratings["overall"], rng)
        ratings["potential"] = _generate_potential(age, ratings["overall"], rng)
        height, weight = _physical_profile(template, position_group, config, rng)
        primary_position, secondary_position = _positions(position_group, ratings)
        first_name, last_name = _unique_name(faker, forbidden_names, used_names)

        players.append(
            {
                "id": f"player_{index:06d}",
                "firstName": first_name,
                "lastName": last_name,
                "displayName": f"{first_name} {last_name}",
                "age": age,
                "primaryPosition": primary_position,
                "secondaryPosition": secondary_position,
                "positionGroup": position_group,
                "heightInches": height,
                "weightPounds": weight,
                "archetype": _archetype(position_group, ratings),
                "talentTier": tier,
                "ratings": ratings,
                "development": {
                    "truePotential": ratings["potential"],
                    "displayedPotential": _clamp_int(
                        ratings["potential"] + rng.normal(0.0, 3.0), ratings["overall"], 99
                    ),
                    "developmentRate": round(float(rng.uniform(0.80, 1.20)), 3),
                    "volatility": round(float(rng.uniform(0.05, 0.30)), 3),
                },
            }
        )

    if len(players) != total_players:
        raise AssertionError(f"Generated {len(players)} players; expected {total_players}.")

    teams = _assign_teams(players, config, rng)
    league = {
        "schemaVersion": int(config["project"]["schema_version"]),
        "generatedAt": date.today().isoformat(),
        "generationSeed": actual_seed,
        "league": {
            "name": config["project"]["league_name"],
            "season": config["project"]["season_label"],
            "teamCount": len(teams),
            "playerCount": len(players),
        },
        "teams": teams,
        "players": players,
    }
    return league, flatten_players(players)


def flatten_players(players: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for player in players:
        row = {
            key: value
            for key, value in player.items()
            if key not in {"ratings", "development"}
        }
        row.update(player["ratings"])
        row.update({f"development_{key}": value for key, value in player["development"].items()})
        rows.append(row)
    return pd.DataFrame(rows).sort_values(
        ["overall", "displayName"], ascending=[False, True]
    ).reset_index(drop=True)
